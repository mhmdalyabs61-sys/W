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
	TOKEN = flag.String("token", os.Getenv("DISCORD_TOKEN"), "Main Bot Token")
)

func main() {
	flag.Parse()

	if *TOKEN == "" {
		log.Fatalf("Error: Main Bot Token is missing. Set DISCORD_TOKEN environment variable.")
	}

	sess, err := discordgo.New("Bot " + *TOKEN)
	if err != nil {
		log.Fatalf("Invalid main bot token: %v", err)
	}

	// تعريف أمر السلاش
	commands := []*discordgo.ApplicationCommand{
		{
			Name:        "spam",
			Description: "إرسال رسائل بسرعة مع معالجة ذكية للـ Rate Limit",
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
			},
		},
	}

	// استقبال الأوامر والتفاعل معها
	sess.AddHandler(func(s *discordgo.Session, i *discordgo.InteractionCreate) {
		if i.ApplicationCommandData().Name == "spam" {
			options := i.ApplicationCommandData().Options
			optionMap := make(map[string]*discordgo.ApplicationCommandInteractionDataOption, len(options))
			for _, opt := range options {
				optionMap[opt.Name] = opt
			}

			msg := optionMap["message"].StringValue()
			count := int(optionMap["count"].IntValue())
			channelID := i.ChannelID

			// رد فوري مخفي
			s.InteractionRespond(i.Interaction, &discordgo.InteractionResponse{
				Type: discordgo.InteractionResponseChannelMessageWithSource,
				Data: &discordgo.InteractionResponseData{
					Content: "جاري الإرسال بمعالجة ذكية للـ Rate Limits...",
					Flags:   discordgo.MessageFlagsEphemeral,
				},
			})

			// إرسال الرسائل مع القراءة الذكية للحدود
			go func() {
				for j := 0; j < count; j++ {
					_, err := s.ChannelMessageSend(channelID, msg)
					if err != nil {
						// التحقق إذا كان الخطأ هو Rate Limit (رمز 429)
						if restErr, ok := err.(*discordgo.RESTError); ok && restErr.Response != nil && restErr.Response.StatusCode == 429 {
							var ratelimit struct {
								RetryAfter float64 `json:"retry_after"`
							}
							if json.Unmarshal(restErr.ResponseBody, &ratelimit) == nil {
								log.Printf("Hit Rate Limit! Waiting for %.2f seconds...", ratelimit.RetryAfter)
								// ينتظر الوقت المحدد بالضبط اللي طلبه ديسكورد
								time.Sleep(time.Duration(ratelimit.RetryAfter * float64(time.Second)))
								
								// إعادة محاولة إرسال الرسالة الحالية بعد انتهاء الانتظار
								_, err = s.ChannelMessageSend(channelID, msg)
								if err != nil {
									log.Printf("Failed after retry: %v", err)
									break
								}
								continue
							}
						}
						
						log.Printf("Failed to send message: %v", err)
						break
					}
					
					// فاصل سريع جداً بين الرسائل (50 ملي ثانية)
					time.Sleep(50 * time.Millisecond)
				}
			}()
		}
	})

	sess.AddHandler(func(s *discordgo.Session, r *discordgo.Ready) {
		log.Printf("Main Bot logged in as: %v", s.State.User.Username)
	})

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
	sc := make(chan os
