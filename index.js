const { Client: BotClient, GatewayIntentBits } = require('discord.js');
const { Client: SelfClient } = require('discord.js-selfbot-v13');
const { joinVoiceChannel, createAudioPlayer, createAudioResource, AudioPlayerStatus } = require('@discordjs/voice');
const play = require('play-dl');

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
        const url = args.join(' '); // لضمان التقاط الرابط كاملاً وبدون أخطاء تقطيع

        if (!volumeLevel || !channelId || !personalToken || !url) {
            return message.reply("⚠️ الاستخدام الصحيح: `!play [خفيف/عادي/قوي/قوي جدا] [أيدي_الفويس] [توكنك_الشخصي] [الرابط]`");
        }

        message.reply("🔄 جاري معالجة الرابط ودخول حسابك الشخصي...");

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

                let streamData;
                
                // معالجة ذكية وآمنة للرابط بناءً على مصدره
                if (url.includes('tiktok.com') || url.includes('vm.tiktok.com') || url.includes('vt.tiktok.com')) {
                    const searchResults = await play.search(url, { limit: 1 });
                    if (!searchResults || searchResults.length === 0 || !searchResults[0].url) {
                        throw new Error("تعذر جلب مقطع تيك توك، تأكد من صحة الرابط.");
                    }
                    streamData = await play.stream(searchResults[0].url);
                } else {
                    // التحقق من صحة رابط يوتيوب أو استخدامه عبر البث المباشر
                    const validate = await play.validate(url);
                    if (!validate) {
                        throw new Error("رابط يوتيوب غير صالح أو غير مدعوم.");
                    }
                    streamData = await play.stream(url, { discordPlayerCompatibility: true });
                }

                if (!streamData || !streamData.stream) {
                    throw new Error("فشل في استخراج التدفق الصوتي من الرابط.");
                }

                const resource = createAudioResource(streamData.stream, {
                    inputType: streamData.type,
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
