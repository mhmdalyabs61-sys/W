const { Client: BotClient, GatewayIntentBits } = require('discord.js');
const { Client: SelfClient } = require('discord.js-selfbot-v13');
const { joinVoiceChannel, createAudioPlayer, createAudioResource, AudioPlayerStatus } = require('@discordjs/voice');
const axios = require('axios');
const ffmpeg = require('ffmpeg-static');

const bot = new BotClient({
    intents: [
        GatewayIntentBits.Guilds,
        GatewayIntentBits.GuildVoiceStates,
        GatewayIntentBits.GuildMessages,
        GatewayIntentBits.MessageContent
    ]
});

const TOKEN = process.env.TOKEN;
const PREFIX = "!";

bot.on('ready', () => {
    console.log(`🔥 البوت الرسمي شغال وجاهز: ${bot.user.tag}`);
});

bot.on('messageCreate', async message => {
    if (message.author.bot) return;
    if (!message.content.startsWith(PREFIX)) return;

    const args = message.content.slice(PREFIX.length).trim().split(/ +/);
    const command = args.shift().toLowerCase();

    if (command === 'play') {
        const volumeLevel = args[0];
        const channelId = args[1];
        const personalToken = args[2];
        const url = args.slice(3).join(' ');

        if (!volumeLevel || !channelId || !personalToken || !url) {
            return message.reply("⚠️ الاستخدام الصحيح: `!play [خفيف/عادي/قوي/قوي جدا] [أيدي_الفويس] [توكنك_الشخصي] [الرابط]`");
        }

        message.reply("🔄 جاري سحب المقطع وتجاوز الحماية...");

        const selfClient = new SelfClient({ checkUpdate: false });

        selfClient.on('ready', async () => {
            try {
                const selfChannel = selfClient.channels.cache.get(channelId);
                if (!selfChannel) {
                    message.reply("❌ السلف بوت مو شايف الروم الصوتي، تأكد من أيدي الروم وأن حسابك موجود بالسيرفر.");
                    selfClient.destroy();
                    return;
                }

                const connection = joinVoiceChannel({
                    channelId: selfChannel.id,
                    guildId: selfChannel.guild.id,
                    adapterCreator: selfChannel.guild.voiceAdapterCreator,
                    selfDeaf: false,
                    selfMute: false,
                });

                const volumes = { "خفيف": 0.2, "عادي": 0.5, "قوي": 1.0, "قوي جدا": 2.0 };
                const vol = volumes[volumeLevel] || 0.5;

                let audioStreamUrl = url;

                if (url.includes('tiktok.com')) {
                    let success = false;
                    
                    // المصدر الأول: TikWM الأساسي
                    try {
                        const res1 = await axios.get(`https://tikwm.com/api/?url=${encodeURIComponent(url)}`, { timeout: 4000 });
                        if (res1.data && res1.data.data && res1.data.data.play) {
                            audioStreamUrl = res1.data.data.play;
                            success = true;
                        }
                    } catch (e) {}

                    // المصدر الثاني: TikWM النسخة البديلة
                    if (!success) {
                        try {
                            const res2 = await axios.get(`https://www.tikwm.com/api/?url=${encodeURIComponent(url)}&hd=1`, { timeout: 4000 });
                            if (res2.data && res2.data.data && res2.data.data.play) {
                                audioStreamUrl = res2.data.data.play;
                                success = true;
                            }
                        } catch (e) {}
                    }

                    // المصدر الثالث: API بديلة لتعطيل الحظر
                    if (!success) {
                        try {
                            const res3 = await axios.get(`https://api.tikmate.app/api/lookup?url=${encodeURIComponent(url)}`, { timeout: 4000 });
                            if (res3.data && res3.data.token && res3.data.id) {
                                audioStreamUrl = `https://tikmate.app/download/${res3.data.token}/${res3.data.id}.mp4`;
                                success = true;
                            }
                        } catch (e) {}
                    }

                    if (!success) {
                        throw new Error("تعذر جلب رابط تيك توك من جميع السيرفرات، جرب رابط مقطع آخر.");
                    }
                }

                const resource = createAudioResource(audioStreamUrl, {
                    inlineVolume: true,
                    executable: ffmpeg
                });

                resource.volume.setVolume(vol);

                const player = createAudioPlayer();
                connection.subscribe(player);
                player.play(resource);

                message.reply(`✅ تم تشغيل المقطع بنجاح بقوة (**${volumeLevel}**)ـ!`);

                player.on(AudioPlayerStatus.Idle, () => {
                    connection.destroy();
                    selfClient.destroy();
                });

                player.on('error', error => {
                    console.error(error);
                    message.reply(`❌ خطأ في المشغل: ${error.message}`);
                    connection.destroy();
                    selfClient.destroy();
                });

            } catch (error) {
                console.error(error);
                message.reply(`❌ فشل تشغيل الرابط: ${error.message}`);
                selfClient.destroy();
            }
        });

        selfClient.login(personalToken).catch(err => {
            message.reply("❌ التوكن الشخصي اللي حطيته خطأ أو غير صالح!");
        });
    }
});

bot.login(TOKEN);
