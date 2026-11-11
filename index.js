const { Client, GatewayIntentBits } = require('discord.js');
const { joinVoiceChannel, createAudioPlayer, createAudioResource, AudioPlayerStatus } = require('@discordjs/voice');
const gTTS = require('gtts');
const fs = require('fs');

const client = new Client({
    intents: [
        GatewayIntentBits.Guilds,
        GatewayIntentBits.GuildVoiceStates,
        GatewayIntentBits.GuildMessages,
        GatewayIntentBits.MessageContent
    ]
});

// توكن البوت الرسمي (يسحبه من إعدادات البيئة في جيتهب أو الاستضافة)
const TOKEN = process.env.TOKEN;
const PREFIX = "!";

client.on('ready', () => {
    console.log(`🔥 البوت شغال وجاهز باسم: ${client.user.tag}`);
});

client.on('messageCreate', async message => {
    if (message.author.bot) return;
    if (!message.content.startsWith(PREFIX)) return;

    const args = message.content.slice(PREFIX.length).trim().split(/ +/);
    const command = args.shift().toLowerCase();

    // أمر التشغيل المباشر: !play [قوي/عادي/خفيف] [أيدي الفويس] [النص أو الرابط]
    if (command === 'play') {
        const volumeLevel = args[0];
        const channelId = args[1];
        const text = args.slice(2).join(' ');

        if (!volumeLevel || !channelId || !text) {
            return message.reply("⚠️ الاستخدام الصحيح: `!play [خفيف/عادي/قوي/قوي جدا] [أيدي_الفويس] [النص أو الرابط]`");
        }

        const channel = client.channels.cache.get(channelId);
        if (!channel || channel.type !== 2) { // 2 تعني روم صوتي (GuildVoice)
            return message.reply("❌ أيدي الروم الصوتي خطأ أو البوت ما يشوفه!");
        }

        try {
            // الاتصال بالفويس
            const connection = joinVoiceChannel({
                channelId: channel.id,
                guildId: channel.guild.id,
                adapterCreator: channel.guild.voiceAdapterCreator,
                selfDeaf: false,
                selfMute: false,
            });

            // تحديد قوة الصوت
            const volumes = {
                "خفيف": 0.2,
                "عادي": 0.5,
                "قوي": 1.0,
                "قوي جدا": 2.0
            };
            const vol = volumes[volumeLevel] || 0.5;

            // توليد الصوت
            const gtts = new gTTS(text, 'ar');
            const audioPath = './temp_audio.mp3';

            gtts.save(audioPath, async (err) => {
                if (err) {
                    return message.reply("❌ صارت مشكلة في توليد الصوت.");
                }

                const player = createAudioPlayer();
                const resource = createAudioResource(audioPath, { inlineVolume: true });
                
                // تطبيق مستوى الصوت المختار
                resource.volume.setVolume(vol);

                connection.subscribe(player);
                player.play(resource);

                message.reply(`▶️ تم الدخول للروم وجاري التشغيل بقوة (**${volumeLevel}**) بنجاح!`);

                player.on(AudioPlayerStatus.Idle, () => {
                    if (fs.existsSync(audioPath)) fs.unlinkSync(audioPath);
                });
            });

        } catch (error) {
            console.error(error);
            message.reply(`❌ صار خطأ: ${error.message}`);
        }
    }

    // أمر الخروج: !leave [أيدي الفويس أو السيرفر]
    if (command === 'leave') {
        try {
            const connection = require('@discordjs/voice').getVoiceConnection(message.guild.id);
            if (connection) {
                connection.destroy();
                message.reply("👋 تم الخروج من الفويس.");
            } else {
                message.reply("⚠️ البوت مو متصل بأي روم هنا.");
            }
        } catch (e) {
            message.reply("⚠️ صار خطأ أثناء الخروج.");
        }
    }
});

client.login(TOKEN);
