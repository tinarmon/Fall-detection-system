/**
 * Google Apps Script Webhook สำหรับเชื่อมต่อ LINE Messaging API กับระบบ Pre-Fall Detection 3D
 * 
 * ฟังก์ชัน:
 * 1. ตอบกลับอัตโนมัติเมื่อผู้ใช้เพิ่มเพื่อน (Follow) หรือทักข้อความ (Message)
 * 2. สร้างภาพ QR Code ความละเอียดสูงที่มี User ID / Group ID อัตโนมัติ
 * 3. ส่งทั้งรูปภาพ QR Code และข้อความแนะนำ เพื่อให้ผู้ใช้สามารถนำหน้าจอมือถือมาจ่อหน้ากล้องคอมพิวเตอร์เพื่อสแกนเชื่อมต่อได้ใน 1 วินาที
 * 
 * วิธีการติดตั้ง:
 * 1. เปิด https://script.google.com สร้าง New Project
 * 2. นำโค้ดนี้ไปวางแทนที่ Code.gs
 * 3. ใส่ Channel Access Token ของคุณใน CHANNEL_ACCESS_TOKEN
 * 4. กด Deploy > New deployment > เลือก Web app
 *    - Execute as: Me
 *    - Who has access: Anyone
 * 5. นำ Webhook URL ที่ได้ไปวางใน LINE Developers Console (Messaging API > Webhook URL) แล้วกด Verify / Use Webhook
 */

const CHANNEL_ACCESS_TOKEN = "dk9jyRVq40y3r88uZbiG98tINzh6uBrXZ64QEOtcABhXm3rcDLoBIPi4D6nw6ox6bEVdPdTl7htO8MfI3FERTGF8WMnSnQRhUzSzfOmk5AnTIgp4FFBXSJNhX8SuJYVFDTJJcLJxapSFsuMkQ4ER8AdB04t89/1O/w1cDnyilFU=";

function doPost(e) {
  try {
    const data = JSON.parse(e.postData.contents);
    const events = data.events;

    for (let i = 0; i < events.length; i++) {
      const event = events[i];
      const replyToken = event.replyToken;

      // ทำงานเมื่อมีการเพิ่มเพื่อน (follow) หรือ ส่งข้อความ (message)
      if (event.type === 'follow' || event.type === 'message') {
        const userId = event.source.userId;
        const groupId = event.source.groupId;

        const targetId = groupId || userId;
        const isGroup = Boolean(groupId);

        // สร้างลิงก์ภาพ QR Code ความละเอียดสูงผ่าน HTTPS จาก targetId โดยตรง
        const qrImageUrl = "https://api.qrserver.com/v1/create-qr-code/?size=400x400&data=" + encodeURIComponent(targetId);

        let replyText = "";
        if (isGroup) {
          replyText = "👥 [ข้อมูลกลุ่ม LINE สำหรับระบบแจ้งเตือน]\n\n" +
                      "Group ID ของคุณคือ:\n" + groupId + "\n\n" +
                      "📷 วิธีเชื่อมต่อง่ายที่สุด:\n" +
                      "เปิดภาพ QR Code ด้านบน แล้วนำไปจ่อหน้ากล้องคอมพิวเตอร์ในโปรแกรม เพื่อสแกนเชื่อมต่ออัตโนมัติได้ทันที!";
        } else {
          replyText = "🛡️ [ระบบแจ้งเตือนภัยล้ม AI Alert]\n\n" +
                      "User ID ของคุณคือ:\n" + userId + "\n\n" +
                      "📷 วิธีเชื่อมต่อง่ายที่สุด:\n" +
                      "เปิดภาพ QR Code ด้านบน แล้วนำไปจ่อหน้ากล้องคอมพิวเตอร์ในโปรแกรม เพื่อสแกนเชื่อมต่ออัตโนมัติได้ทันที!";
        }

        // ส่งทั้งรูปภาพ QR Code และข้อความแนะนำกลับไปพร้อมกัน
        sendLineReplyWithQR(replyToken, replyText, qrImageUrl);
      }
    }
  } catch (err) {
    console.error(err);
  }

  return ContentService.createTextOutput(JSON.stringify({status: 'ok'}))
    .setMimeType(ContentService.MimeType.JSON);
}

function sendLineReplyWithQR(replyToken, text, qrImageUrl) {
  const url = "https://api.line.me/v2/bot/message/reply";
  const payload = {
    replyToken: replyToken,
    messages: [
      {
        type: "image",
        originalContentUrl: qrImageUrl,
        previewImageUrl: qrImageUrl
      },
      {
        type: "text",
        text: text
      }
    ]
  };

  UrlFetchApp.fetch(url, {
    method: "post",
    headers: {
      "Content-Type": "application/json",
      "Authorization": "Bearer " + CHANNEL_ACCESS_TOKEN
    },
    payload: JSON.stringify(payload)
  });
}
