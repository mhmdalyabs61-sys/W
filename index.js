const { Client: BotClient, GatewayIntentBits } = require('discord.js');
const { Client: SelfClient } = require('discord.js-selfbot-v13');
const { joinVoiceChannel, createAudioPlayer, createAudioResource, AudioPlayerStatus } = require('@discordjs/voice');
const axios = require('axios');
const ffmpeg = require('ffmpeg-static');
const { spawn } = require('child_process');

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
                    
                    try {
                        const apiRes = await axios.get(`https://tikwm.com/api/?url=${encodeURIComponent(url)}`, { timeout: 5000 });
                        if (apiRes.data && apiRes.data.data && apiRes.data.data.play) {
                            audioStreamUrl = apiRes.data.data.play;
                            success = true;
                        }
                    } catch (e) {}

                    if (!success) {
                        try {
                            const altRes = await axios.get(`https://www.tikwm.com/api/?url=${encodeURIComponent(url)}&hd=1`, { timeout: 5000 });
                            if (altRes.data && altRes.data.data && altRes.data.data.play) {
                                audioStreamUrl = altRes.data.data.play;
                                success = true;
                            }
                        } catch (e) {}
                    }

                    if (!success) {
                        throw new Error("تعذر جلب رابط تيك توك، قد يكون المقطع محذوفاً أو الحساب خاصاً.");
                    }
                }

                // دالة توليد مسار الصوت الصافي عبر تشغيل FFmpeg يدويًا لضمان خروج الصوت للروم
                const createFFmpegStream = (streamUrl) => {
                    const ffmpegProcess = spawn(ffmpeg, [
                        '-i', streamUrl,
                        '-analyzeduration', '0',
                        '-loglevel', '0',
                        '-f', 's16le',
                        '-ar', '48000',
                        '-ac', '2',
                        'pipe:1'
                    ]);

                    ffmpegProcess.on('error', (err) => {
                        console.error('FFmpeg error:', err);
                    });

                    return ffmpegProcess.stdout;
                };

                const audioStream = createFFmpegStream(audioStreamUrl);

                const resource = createAudioResource(audioStream, {
                    inlineVolume: true
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

            }チャ (error) {
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
