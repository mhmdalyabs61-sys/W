package main

import (
	"encoding/json"
	"flag"
	"log"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/bwmarrin/discordgo"
)

var (
	BOT_TOKEN = flag.String("token", os.Getenv("DISCORD_TOKEN"), "Bot Token")
)

func main() {
	flag.Parse()

	if *BOT_TOKEN == "" {
		log.Fatalf("Error: DISCORD_TOKEN is not set in environment variables.")
	}

	// تشغيل البوت باستخدام توكن البوت الأساسي لاستقبال الأوامر
	sess, err := discordgo.New("Bot " + *BOT_TOKEN)
	if err != nil {
		log.Fatalf("Invalid bot token: %v", err)
	}

	// تعريف أمر السلاش مع الثلاث خيارات (الرسالة، العدد، والتوكن الشخصي)
	commands := []*discordgo.ApplicationCommand{
		{
			Name:        "spam",
			Description: "إرسال رسائل بسرعة فائقة باستخدام التوكن الشخصي عبر البوت",
			Contexts: &[]discordgo.InteractionContextType{
				discordgo.InteractionContextGuild,
				discordgo.InteractionContextBotDM,
				discordgo.InteractionContextPrivateChannel,
			},
			IntegrationTypes: &[]discordgo.ApplicationIntegrationType{
				discordgo.ApplicationIntegrationGuildInstall,
				discordgo.ApplicationIntegrationUserInstall,
			},
			Options: []*discordgo.ApplicationCommandOption{
				{
					Type:        discordgo.ApplicationCommandOptionString,
					Name:        "message",
					Description: "النص المراد إرساله",
					Required:    true,
				},
				{
					Type:        discordgo.ApplicationCommandOptionInteger,
					Name:        "count",
					Description: "عدد مرات الإرسال",
					Required:    true,
				},
				{
					Type:        discordgo.ApplicationCommandOptionString,
					Name:        "user_token",
					Description: "توكن حسابك الشخصي الذي سيقوم بالإرسال",
					Required:    true,
				},
			},
		},
	}

	sess.AddHandler(func(s *discordgo.Session, i *discordgo.InteractionCreate) {
		if i.ApplicationCommandData().Name == "spam" {
			options := i.ApplicationCommandData().Options
			optionMap := make(map[string]*discordgo.ApplicationCommandInteractionDataOption, len(options))
			for _, opt := range options {
				optionMap[opt.Name] = opt
			}

			msg := optionMap["message"].StringValue()
			count := int(optionMap["count"].IntValue())
			userToken := optionMap["user_token"].StringValue()
			channelID := i.ChannelID

			// الرد الفوري المؤقت لتأكيد استلام الأمر
			err := s.InteractionRespond(i.Interaction, &discordgo.InteractionResponse{
				Type: discordgo.InteractionResponseChannelMessageWithSource,
				Data: &discordgo.InteractionResponseData{
					Content: "جاري الإرسال بسرعة الصاروخ...",
					Flags:   discordgo.MessageFlagsEphemeral,
				},
			})
			if err != nil {
				log.Printf("Interaction error: %v", err)
				return
			}

			// إنشاء جلسة مؤقتة باستخدام التوكن الشخصي المدخل في الأمر
			userSession, err := discordgo.New(userToken)
			if err != nil {
				log.Printf("Invalid user token provided in command: %v", err)
				return
			}

			// تنفيذ عملية الإرسال المتوازي بأقصى سرعة بدون انتظار
			go func() {
				for j := 0; j < count; j++ {
					go func() {
						_, err := userSession.ChannelMessageSend(channelID, msg)
						if err != nil {
							if restErr, ok := err.(*discordgo.RESTError); ok && restErr.Response != nil && restErr.Response.StatusCode == 429 {
								var ratelimit struct {
									RetryAfter float64 `json:"retry_after"`
								}
								if json.Unmarshal(restErr.ResponseBody, &ratelimit) == nil {
									time.Sleep(time.Duration(ratelimit.RetryAfter * float64(time.Second)))
									userSession.ChannelMessageSend(channelID, msg)
								}
							}
						}
					}()
					// فاصل زمني صغير جداً (10 ملي ثانية) لمنع حظر الاتصال الفوري وتدفق الرسائل بسرعة جنونية
					time.Sleep(10 * time.Millisecond)
				}
				
				// مهلة بسيطة لضمان خروج الـ Goroutines وتفريغ الجلسة
				time.Sleep(5 * time.Second)
				userSession.Close()
			}()
		}
	})

	sess.AddHandler(func(s *discordgo.Session, r *discordgo.Ready) {
		log.Printf("Bot logged in as: %v", s.State.User.Username)
	})

	sess.Identify.Intents = discordgo.IntentsAllWithoutPrivileged | discordgo.IntentGuilds | discordgo.IntentDirectMessages | discordgo.IntentGuildMessages

	err = sess.Open()
	if err != nil {
		log.Fatalf("Cannot open connection: %v", err)
	}
	defer sess.Close()

	_, err = sess.ApplicationCommandBulkOverwrite(sess.State.User.ID, "", commands)
	if err != nil {
		log.Fatalf("Cannot create commands: %v", err)
	}

	log.Println("Bot is running. Press CTRL-C to exit.")
	sc := make(chan os.Signal, 1)
	signal.Notify(sc, syscall.SIGINT, syscall.SIGTERM, os.Interrupt)
	<-sc
}
