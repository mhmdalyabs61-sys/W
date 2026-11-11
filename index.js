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

        message.reply("🔄 جاري سحب مقطع التيك توك وبث الصوت...");

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

                // جلب البيانات مع تحديد الـ Stream بشكل دقيق جداً
                const audioResponse = await axios.get(directVideoUrl, {
                    responseType: 'stream',
                    headers: { 'User-Agent': 'Mozilla/5.0' }
                });

                // إنشاء المورد الصوتي مع إجبار FFmpeg على معالجة الصوت وضبط الترددات
                const resource = createAudioResource(audioResponse.data, {
                    inlineVolume: true,
                    executable: ffmpeg,
                    inputType: 'webm/opus' // أو اتركه تلقائي مع الـ FFmpeg args
                });

                resource.volume.setVolume(vol);

                const player = createAudioPlayer();
                connection.subscribe(player);
                player.play(resource);

                message.reply(`✅ بدأ بث الصوت في الروم بقوة (**${volumeLevel}**)ـ!`);

                player.on(AudioPlayerStatus.Playing, () => {
                    console.log('▶️ المشغل بدأ ببث الصوت بنجاح.');
                });

                player.on(AudioPlayerStatus.Idle, () => {
                    connection.destroy();
                    selfClient.destroy();
                });

                player.on('error', error => {
                    console.error('خطأ في المشغل:', error);
                    message.reply(`❌ خطأ في المشغل الصوتي: ${error.message}`);
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
            message.reply("❌ التوكن الشخصي اللي حطيته خطأ أو غير صالح!");
        });
    }
});

bot.login(TOKEN);
