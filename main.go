package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"log"
	"os"
	"os/signal"
	"strings"
	"sync"
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

	// تعريف أمر السلاش مع دعم التشغيل في الخاص وفي السيرفرات (User Install & DMs)
	commands := []*discordgo.ApplicationCommand{
		{
			Name:        "spam",
			Description: "إرسال رسائل بسرعة عالية مع احترام حدود ديسكورد لكل بوت",
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
					Description: "عدد مرات الإرسال لكل بوت",
					Required:    true,
				},
				{
					Type:        discordgo.ApplicationCommandOptionString,
					Name:        "tokens",
					Description: "توكنات البوتات الفرعية (افصل بينها بفاصلة أو مسافة)",
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
			rawTokens := optionMap["tokens"].StringValue()
			channelID := i.ChannelID

			// تقسيم التوكنات وتصفيتها
			tokens := strings.FieldsFunc(rawTokens, func(r rune) bool {
				return r == ',' || r == ' ' || r == '\n'
			})

			// رد فوري مخفي لعدم تعليق ديسكورد
			s.InteractionRespond(i.Interaction, &discordgo.InteractionResponse{
				Type: discordgo.InteractionResponseChannelMessageWithSource,
				Data: &discordgo.InteractionResponseData{
					Content: fmt.Sprintf("جاري التنفيذ الذكي عبر %d بوت مع إدارة الـ Rate Limits...", len(tokens)),
					Flags:   discordgo.MessageFlagsEphemeral,
				},
			})

			// تشغيل البوتات الفرعية بالتوازي التام
			go executeWorkerBots(tokens, channelID, msg, count)
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
	sc := make(chan os.Signal, 1)
	signal.Notify(sc, syscall.SIGINT, syscall.SIGTERM, os.Interrupt)
	<-sc
	log.Println("Shutting down gracefully.")
}

// دالة تنفيذ الإرسال المتوازي مع معالجة الـ Rate Limit لكل بوت بشكل مستقل
func executeWorkerBots(tokens []string, channelID string, message string, count int) {
	var wg sync.WaitGroup

	for idx, t := range tokens {
		cleanToken := strings.TrimSpace(t)
		if cleanToken == "" {
			continue
		}

		wg.Add(1)
		go func(workerID int, botToken string) {
			defer wg.Done()

			workerSess, err := discordgo.New("Bot " + botToken)
			if err != nil {
				log.Printf("[Worker %d] Invalid token: %v", workerID, err)
				return
			}

			for j := 0; j < count; j++ {
				_, err := workerSess.ChannelMessageSend(channelID, message)
				if err != nil {
					// التحقق إذا كان الخطأ هو Rate Limit (رمز 429)
					if restErr, ok := err.(*discordgo.RESTError); ok && restErr.Response != nil && restErr.Response.StatusCode == 429 {
						var ratelimit struct {
							RetryAfter float64 `json:"retry_after"`
						}
						if json.Unmarshal(restErr.ResponseBody, &ratelimit) == nil {
							log.Printf("[Worker %d] Hit Rate Limit. Waiting for %.2f seconds...", workerID, ratelimit.RetryAfter)
							// إيقاف هذا البوت لوحده للوقت المحدّد دون إيقاف باقي البوتات
							time.Sleep(time.Duration(ratelimit.RetryAfter * float64(time.Second)))
							
							// إعادة محاولة إرسال الرسالة الحالية بعد انتهاء فترة الانتظار
							_, err = workerSess.ChannelMessageSend(channelID, message)
							if err != nil {
								log.Printf("[Worker %d] Failed after retry: %v", workerID, err)
								break
							}
							continue
						}
					}
					
					// في حال حدوث أي خطأ آخر، يتوقف هذا البوت فقط
					log.Printf("[Worker %d] Error: %v", workerID, err)
					break
				}
			}
		}(idx+1, cleanToken)
	}

	wg.Wait()
	log.Println("All worker tasks completed.")
}
