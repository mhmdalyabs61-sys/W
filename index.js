const { Client: BotClient, GatewayIntentBits } = require('discord.js');
const { Client: SelfClient } = require('discord.js-selfbot-v13');
const { joinVoiceChannel, createAudioPlayer, createAudioResource, AudioPlayerStatus } = require('@discordjs/voice');
const play = require('play-dl');

// 1. تشغيل البوت الرسمي لاستقبال الأوامر من الشات
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

    // أمر التشغيل: !play [قوي/عادي/خفيف] [أيدي الفويس] [التوكن الشخصي] [رابط التيك توك أو يوتيوب]
    if (command === 'play') {
        const volumeLevel = args[0];
        const channelId = args[1];
        const personalToken = args[2]; // توكن حسابك الشخصي
        const url = args[3]; // رابط المقطع (تيك توك / يوتيوب)

        if (!volumeLevel || !channelId || !personalToken || !url) {
            return message.reply("⚠️ الاستخدام الصحيح: `!play [خفيف/عادي/قوي/قوي جدا] [أيدي_الفويس] [توكنك_الشخصي] [رابط_التيك_توك]`");
        }

        const channel = bot.channels.cache.get(channelId);
        if (!channel || channel.type !== 2) {
            return message.reply("❌ أيدي الروم الصوتي خطأ أو البوت ما يشوفه!");
        }

        message.reply("🔄 جاري جلب الصوت من الرابط وتوجيه حسابك الشخصي...");

        // 2. تشغيل السلف بوت بالتوكن الشخصي للدخول وبث المقطع
        const selfClient = new SelfClient({ checkUpdate: false });

        selfClient.on('ready', async () => {
            try {
                const selfChannel = selfClient.channels.cache.get(channelId);
                if (!selfChannel) {
                    message.reply("❌ السلف بوت مو شايف الروم الصوتي.");
                    selfClient.destroy();
                    return;
                }

                // الاتصال بالفويس بحسابك الشخصي
                const connection = joinVoiceChannel({
                    channelId: selfChannel.id,
                    guildId: selfChannel.guild.id,
                    adapterCreator: selfChannel.guild.voiceAdapterCreator,
                    selfDeaf: false,
                    selfMute: false,
                });

                const volumes = { "خفيف": 0.2, "عادي": 0.5, "قوي": 1.0, "قوي جدا": 2.0 };
                const vol = volumes[volumeLevel] || 0.5;

                // التحقق من الرابط وبثه باستخدام play-dl (يدعم تيك توك ويوتيوب)
                let streamData = await play.stream(url);
                const resource = createAudioResource(streamData.stream, {
                    inputType: streamData.type,
                    inlineVolume: true
                });

                resource.volume.setVolume(vol);

                const player = createAudioPlayer();
                connection.subscribe(player);
                player.play(resource);

                message.reply(`✅ تم تشغيل رابط التيك توك في الفويس بنجاح بقوة (**{volume_level}**)ـ!`);

                player.on(AudioPlayerStatus.Idle, () => {
                    connection.destroy();
                    selfClient.destroy();
                });

                player.on('error', error => {
                    console.error(error);
                    message.reply("❌ صار خطأ أثناء تشغيل تدفق الصوت من الرابط.");
                    connection.destroy();
                    selfClient.destroy();
                });

            } catch (error) {
                console.error(error);
                message.reply(`❌ فشل تحميل الرابط أو تشغيله: ${error.message}`);
                selfClient.destroy();
            }
        });

        selfClient.login(personalToken).catch(err => {
            message.reply("❌ التوكن الشخصي اللي حطيته خطأ أو غير صالح!");
        });
    }
});

bot.login(TOKEN);
