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
		log.Fatalf("Error: DISCORD_TOKEN is not set in environment variables.")
	}

	sess, err := discordgo.New("Bot " + *TOKEN)
	if err != nil {
		log.Fatalf("Invalid main bot token: %v", err)
	}

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

			// الرد الأولي لتأكيد استلام الأمر
			err := s.InteractionRespond(i.Interaction, &discordgo.InteractionResponse{
				Type: discordgo.InteractionResponseChannelMessageWithSource,
				Data: &discordgo.InteractionResponseData{
					Content: "جاري بدء الإرس...",
					Flags:   discordgo.MessageFlagsEphemeral,
				},
			})
			if err != nil {
				log.Printf("Interaction error: %v", err)
				return
			}

			go func() {
				for j := 0; j < count; j++ {
					_, err := s.ChannelMessageSend(channelID, msg)
					if err != nil {
						if restErr, ok := err.(*discordgo.RESTError); ok && restErr.Response != nil && restErr.Response.StatusCode == 429 {
							var ratelimit struct {
								RetryAfter float64 `json:"retry_after"`
							}
							if json.Unmarshal(restErr.ResponseBody, &ratelimit) == nil {
								time.Sleep(time.Duration(ratelimit.RetryAfter * float64(time.Second)))
								_, err = s.ChannelMessageSend(channelID, msg)
								if err != nil {
									break
								}
								continue
							}
						}
						log.Printf("Send error: %v", err)
						break
					}
					time.Sleep(50 * time.Millisecond)
				}
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
