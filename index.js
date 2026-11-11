const { Client: BotClient, GatewayIntentBits } = require('discord.js');
const { Client: SelfClient } = require('discord.js-selfbot-v13');
const { joinVoiceChannel, createAudioPlayer, createAudioResource, AudioPlayerStatus } = require('@discordjs/voice');
const axios = require('axios');
const { spawn } = require('child_process');
const ffmpegPath = require('ffmpeg-static');

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

        message.reply("🔄 جاري الاتصال وبث الصوت...");

        const selfClient = new SelfClient({ checkUpdate: false });

        selfClient.on('ready', async () => {
            try {
                const selfChannel = selfClient.channels.cache.get(channelId);
                if (!selfChannel) {
                    message.reply("❌ السلف بوت مو شايف الروم الصوتي، تأكد من أيدي الروم.");
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

                let directVideoUrl = url;

                if (url.includes('tiktok.com')) {
                    const response = await axios.get(`https://tikwm.com/api/?url=${encodeURIComponent(url)}`, {
                        headers: { 'User-Agent': 'Mozilla/5.0' },
                        timeout: 8000
                    });
                    
                    if (response.data && response.data.data && response.data.data.play) {
                        directVideoUrl = response.data.data.play;
                    } else {
                        throw new Error("فشل استخراج الرابط المباشر للمقطع.");
                    }
                }

                // تشغيل FFmpeg مع معالجة الأخطاء والـ Stdio بشكل مستقر
                const ffmpegProcess = spawn(ffmpegPath, [
                    '-i', directVideoUrl,
                    '-vn',
                    '-ar', '48000',
                    '-ac', '2',
                    '-f', 's16le',
                    'pipe:1'
                ], { stdio: ['ignore', 'pipe', 'ignore'] });

                const resource = createAudioResource(ffmpegProcess.stdout, {
                    inlineVolume: true
                });

                resource.volume.setVolume(vol);

                const player = createAudioPlayer();
                connection.subscribe(player);
                player.play(resource);

                message.reply(`✅ تم تشغيل المقطع بنجاح بقوة (**${volumeLevel}**)ـ!`);

                player.on(AudioPlayerStatus.Idle, () => {
                    if (!ffmpegProcess.killed) ffmpegProcess.kill();
                    connection.destroy();
                    selfClient.destroy();
                });

                player.on('error', error => {
                    console.error('خطأ المشغل:', error);
                    if (!ffmpegProcess.killed) ffmpegProcess.kill();
                    connection.destroy();
                    selfClient.destroy();
                });

            } catch (error) {
                console.error(error);
                message.reply(`❌ فشل التشغيل: ${error.message}`);
                selfClient.destroy();
            }
        });

        selfClient.login(personalToken).catch(err => {
            message.reply("❌ التوكن الشخصي خطأ!");
        });
    }
});

bot.login(TOKEN);
