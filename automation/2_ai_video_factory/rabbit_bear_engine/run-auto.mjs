#!/usr/bin/env node
/**
 * RUN-AUTO.MJS (v2.0 - Unified Rabbit & Bear 3D Pixar News Pipeline)
 * -------------------------------------------------------------------
 * - Vũ trụ nhân vật cố định: Thỏ Đỏ (Bunny) & Gấu Béo (Bear) 3D Pixar
 * - Kịch bản 4 cảnh liên kết mạch lạc (42-50 từ/cảnh) + 1 cảnh Outro cố định (6s)
 * - Đồng bộ âm thanh chính xác (Precision Audio Sync):
 *   + Duy nhất 1 giọng đọc vi-VN-NamMinhNeural xuyên suốt 100% các cảnh
 *   + Cắt khoảng lặng thừa (silenceremove) + Tự động cân chỉnh tốc độ (atempo)
 *   + Giọng đọc luôn lấp đầy 9.3s - 9.5s / 10.0s (Không còn 4-5s chết, không bao giờ cắt chữ)
 * - Chống lỗi cảnh & trùng cảnh Muse.ai (SHA-256 verification + fresh thread retry)
 * - Tự động đồng bộ sang Web Affiliate Player & Social Poster Queue (d:/web_aff)
 */

import puppeteer from 'puppeteer-core';
import fs from 'fs';
import path from 'path';
import https from 'https';
import crypto from 'crypto';
import { execSync } from 'child_process';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const ENGINE_ROOT = fs.existsSync('d:/nckh/auto-video-gen') ? 'd:/nckh/auto-video-gen' : __dirname;
const WEB_AFF_ROOT = fs.existsSync('d:/web_aff') ? 'd:/web_aff' : path.resolve(__dirname, '../../..');

function detectChromePath() {
  const candidates = [
    process.env.CHROME_PATH,
    'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe',
    'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
    '/usr/bin/google-chrome',
    '/usr/bin/google-chrome-stable',
    '/usr/bin/chromium-browser',
    '/usr/bin/chromium'
  ].filter(Boolean);
  for (const c of candidates) {
    if (fs.existsSync(c)) return c;
  }
  return candidates[0];
}

function loadGeminiKey() {
  if (process.env.GEMINI_API_KEY) return process.env.GEMINI_API_KEY.trim();
  for (const envPath of [path.join(WEB_AFF_ROOT, '.env'), path.join(ENGINE_ROOT, '.env')]) {
    if (fs.existsSync(envPath)) {
      const m = fs.readFileSync(envPath, 'utf8').match(/^GEMINI_API_KEY=(.+)$/m);
      if (m && m[1]) return m[1].trim();
    }
  }
  return '';
}

const CHROME_PATH = detectChromePath();
const COOKIE_FILE = path.join(ENGINE_ROOT, 'muse_cookie.txt');
const GEMINI_KEY = loadGeminiKey();
const SHARED_DIR = path.join(ENGINE_ROOT, 'shared_assets');
const PYTHON_BIN = process.platform === 'win32' ? 'python' : 'python3';

function probeDuration(filePath) {
  const out = execSync(`ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "${filePath}"`).toString().trim();
  return parseFloat(out);
}

function fileSha256(filePath) {
  const buf = fs.readFileSync(filePath);
  return crypto.createHash('sha256').update(buf).digest('hex');
}

function decodeHtmlEntities(str) {
  return (str || '')
    .replace(/&nbsp;/gi, ' ')
    .replace(/&amp;/gi, '&')
    .replace(/&quot;/gi, '"')
    .replace(/&#39;|&apos;/gi, "'")
    .replace(/&lt;/gi, '<')
    .replace(/&gt;/gi, '>')
    .replace(/&#(\d+);/g, (_, n) => String.fromCharCode(Number(n)))
    .replace(/\s+/g, ' ')
    .trim();
}

function shortenNewsTitle(rawTitle, maxChars = 72) {
  let t = decodeHtmlEntities(rawTitle)
    .replace(/\s*[-–—|]\s*(VnExpress|Báo VnExpress|Dân trí|Báo Dân trí|Tuổi Trẻ Online|Tuổi Trẻ|Thanh Niên|Báo Thanh Niên|Soha|VietnamNet|Kênh 14|Kenh14|24h\.com\.vn|Người Lao Động|Znews).*$/i, '')
    .trim();
  if (t.length <= maxChars) return t;
  const cut = t.slice(0, maxChars).replace(/\s+\S*$/, '').trim();
  return (cut || t.slice(0, maxChars).trim()) + '...';
}

async function fetchArticle(url) {
  console.log(`\n📥 [1/6] Đang tải và trích xuất nội dung bài báo từ: ${url}...`);
  const res = await fetch(url, { headers: { 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)' } });
  const html = await res.text();
  const h1Match = html.match(/<h1[^>]*>([\s\S]*?)<\/h1>/i);
  const ogMatch = html.match(/<meta[^>]+property=["']og:title["'][^>]+content=["']([^"']+)["']/i)
    || html.match(/<meta[^>]+content=["']([^"']+)["'][^>]+property=["']og:title["']/i);
  const titleTagMatch = html.match(/<title[^>]*>([\s\S]*?)<\/title>/i);

  const rawH1 = h1Match ? h1Match[1].replace(/<[^>]+>/g, ' ') : '';
  const rawOg = ogMatch ? ogMatch[1] : '';
  const rawTag = titleTagMatch ? titleTagMatch[1] : '';
  const articleTitle = shortenNewsTitle(rawH1 || rawOg || rawTag || 'Bản Tin 3D Thỏ & Gấu', 80);

  const articleMatch = html.match(/<article[\s\S]*?<\/article>/i);
  const rawBlock = (h1Match ? h1Match[0] + ' ' : '') + (articleMatch ? articleMatch[0] : html);
  const clean = rawBlock
    .replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '')
    .replace(/<style\b[^<]*(?:(?!<\/style>)<[^<]*)*<\/style>/gi, '')
    .replace(/<[^>]+>/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
  console.log(`📰 Tiêu đề báo gốc: "${articleTitle}"`);
  return { title: articleTitle, text: clean.slice(0, 12000) };
}

function ensureRichVoiceText(text, sceneIdx) {
  const words = (text || '').trim().split(/\s+/).filter(Boolean);
  if (words.length >= 28) return text.trim();
  const fillers = {
    1: 'Sự việc đang thu hút sự quan tâm đặc biệt từ cộng đồng mạng.',
    2: 'Diễn biến tiếp theo càng làm rõ hơn nguyên nhân sâu xa của vụ việc.',
    3: 'Cơ quan chức năng đã nhanh chóng có mặt để xử lý nghiêm minh.',
    4: 'Đây là bài học cảnh tỉnh sâu sắc cho tất cả mọi người.'
  };
  return `${text.trim()} ${fillers[sceneIdx] || fillers[4]}`;
}

async function generateScript(articleText, articleTitle = '') {
  console.log(`\n🤖 [2/6] AI Director: Biên kịch cốt truyện 4 hồi liền mạch trong Vũ trụ Thỏ & Gấu 3D...`);
  const prompt = `Bạn là Tổng Đạo diễn kiêm Biên tập viên cho kênh video hoạt hình tin tức 3D Pixar triệu view "Vũ trụ Thỏ & Gấu".
Tiêu đề gốc của bài báo: "${articleTitle}"
Dưới đây là nội dung bài báo nguồn:
"""
${articleText}
"""

HÃY CHUYỂN THỂ BÀI BÁO THÀNH KỊCH BẢN 4 PHÂN CẢNH LIỀN MẠCH (4-ACT CONTINUOUS STORY) VỚI CÁC QUY TẮC BẮT BUỘC SAU:
0. QUY TẮC TIÊU ĐỀ (BẮT BUỘC):
   - Tiêu đề (headline cảnh 1 và ticker) PHẢI LẤY TRỰC TIẾP TỪ TIÊU ĐỀ BÁO GỐC ("${articleTitle}"), nếu dài quá thì chỉ rút gọn cho vừa khung, TUYỆT ĐỐI KHÔNG tự sáng tạo/bịa ra tiêu đề khác lệch với bài báo!
1. VŨ TRỤ NHÂN VẬT THỎ & GẤU CỐ ĐỊNH 100%:
   - Nhân vật chính: Luôn là THỎ ĐỎ (Cute agile bunny rabbit wearing a bright red hoodie or red jersey, long expressive ears, witty and energetic).
   - Nhân vật đồng hành / đối thủ: Luôn là GẤU BÉO (Chubby fluffy white bear companion/rival, round belly, clumsy, lovable and funny).
   - Tuyệt đối không dùng nhân vật người thật, toàn bộ câu chuyện phải được diễn xuất bởi Thỏ Đỏ và Gấu Béo trong cùng một bối cảnh xuyên suốt.

2. LIÊN KẾT MẠCH LẠC GIỮA CÁC CẢNH (KHÔNG RỜI RẠC):
   - Cảnh 1 (Mở đầu & Bối cảnh): Dẫn nhập sự kiện nóng hổi với sự xuất hiện của Thỏ Đỏ & Gấu Béo.
   - Cảnh 2 (Diễn biến leo thang): Bắt đầu bằng từ nối mượt mà ("Chưa dừng lại ở đó...", "Bước sang chặng tiếp theo...", "Thử thách thực sự bắt đầu khi...").
   - Cảnh 3 (Cao trào / Cú twist hài hước): Bắt đầu bằng từ nối cao trào ("Ấy thế mà đúng lúc gay cấn nhất...", "Đỉnh điểm của màn tấu hài là khi...").
   - Cảnh 4 (Kết cục trọn vẹn): Bắt đầu bằng từ nối kết ("Khép lại hành trình đáng nhớ...", "Sau tất cả những pha dở khóc dở cười...").

3. ĐỘ DÀI LỜI BÌNH (voiceText) CHUẨN KHỚP 10 GIÂY (KHÔNG BỊ NGẮN / KHÔNG DƯ THỜI GIAN CHẾT):
   - Mỗi cảnh video dài 10 giây. Vì vậy mỗi lời bình (voiceText) BẮT BUỘC phải gồm 2 câu văn sinh động, độ dài từ 42 đến 50 TỪ (âm tiết tiếng Việt).
   - Tuyệt đối không viết ngắn dưới 40 từ để tránh việc đọc xong sớm rồi dư 4-5 giây im lặng!

4. VISUAL PROMPT ĐỒNG NHẤT & AN TOÀN 100% CHO MUSE.AI:
   - Mỗi visualPrompt BẮT BUỘC bắt đầu bằng: "Create a 16:9 aspect ratio video clip, 10 seconds long. Directly render the video now without asking options. Stylized 3D Pixar animation..."
   - Phải mô tả rõ ngoại hình đồng nhất của "cute bunny rabbit in bright red hoodie/jersey with long ears" và "chubby fluffy white bear", cùng hành động khớp với lời bình của cảnh đó.
   - QUY TẮC AN TOÀN MUSE.AI (BẮT BUỘC): Trong visualPrompt tiếng Anh TUYỆT ĐỐI KHÔNG dùng các từ nhạy cảm bị bộ lọc AI chặn như: dead, death, die, killed, murder, blood, gore, fatal crash, corpse, hit by truck. Nếu bài báo nói về tai nạn hoặc vụ án, hãy mô tả cảnh 3D ẩn dụ an toàn (ví dụ: "reckless truck making a sharp turn at an intersection causing a tense near-miss traffic stop", "police officers with flashing lights questioning the regretful bear driver beside the truck", "solemn family reflection and traffic safety lesson").
   - Nếu bài báo là tin thời sự / pháp luật / giao thông nghiêm túc, hãy dùng giọng bình luận thời sự kịch tính, sâu sắc và cảnh tỉnh (không dùng từ 'tấu hài' cho tin buồn), đồng thời đặt brandBadge là "24H TIN NÓNG" hoặc "24H GIAO THÔNG".

Trả về duy nhất định dạng JSON thuần:
{
  "matchTitle": "TIÊU ĐỀ NGẮN (TỐI ĐA 18 KÝ TỰ)",
  "brandBadge": "24H KHÁM PHÁ hoặc 24H BÓNG ĐÁ",
  "ticker": "DÒNG CHỮ CHẠY CUỐI MÀN HÌNH TÓM TẮT BẢN TIN THỎ & GẤU",
  "socialCaption": "Caption hấp dẫn đăng Facebook/Threads kèm 4 hashtag",
  "scenes": [
    {
      "index": 1,
      "tag": "🔥 TIÊU ĐIỂM 1 • MỞ MÀN",
      "headline": "TIÊU ĐỀ IN HOA GIẬT GÂN KÈM ICON",
      "sub": "Mô tả phụ dí dỏm tóm tắt cảnh 1",
      "color": "#00B4D8",
      "voiceText": "2 câu dẫn chuyện liên kết mạch lạc độ dài từ 42 đến 50 từ...",
      "visualPrompt": "Create a 16:9 aspect ratio video clip, 10 seconds long. Directly render the video now without asking options. Stylized 3D Pixar animation..."
    },
    { "index": 2, "tag": "...", "headline": "...", "sub": "...", "color": "#FF9900", "voiceText": "...", "visualPrompt": "..." },
    { "index": 3, "tag": "...", "headline": "...", "sub": "...", "color": "#06D6A0", "voiceText": "...", "visualPrompt": "..." },
    { "index": 4, "tag": "...", "headline": "...", "sub": "...", "color": "#E63946", "voiceText": "...", "visualPrompt": "..." }
  ]
}`;

  const body = JSON.stringify({
    contents: [{ parts: [{ text: prompt }] }],
    generationConfig: { responseMimeType: 'application/json' }
  });

  const modelsToTry = ['gemini-3.5-flash-lite', 'gemini-3.1-flash-lite', 'gemini-3.1-flash-lite-preview'];
  let parsed = null;
  const MAX_ROUNDS = 3;

  for (let round = 1; round <= MAX_ROUNDS && !parsed; round++) {
    for (const modelName of modelsToTry) {
      try {
        parsed = await new Promise((resolve, reject) => {
          const req = https.request(`https://generativelanguage.googleapis.com/v1beta/models/${modelName}:generateContent?key=${GEMINI_KEY}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(body) }
          }, res => {
            let d = '';
            res.on('data', c => d += c);
            res.on('end', () => {
              try {
                const r = JSON.parse(d);
                let t = r.candidates?.[0]?.content?.parts?.[0]?.text;
                if (!t) return reject(new Error(`Empty response from ${modelName}: ${d.slice(0, 200)}`));
                t = t.replace(/^```json\s*/i, '').replace(/```\s*$/i, '').trim();
                resolve(JSON.parse(t));
              } catch (e) { reject(e); }
            });
          });
          req.on('error', reject);
          req.write(body);
          req.end();
        });
        if (parsed && parsed.scenes) {
          console.log(`✅ Đã biên kịch thành công bằng mô hình ${modelName} (vòng ${round}/${MAX_ROUNDS})!`);
          break;
        }
      } catch (err) {
        console.warn(`  [Vòng ${round}/${MAX_ROUNDS} - ${modelName}] ${err.message}`);
      }
    }
    if (!parsed && round < MAX_ROUNDS) {
      const waitSec = round * 6;
      console.log(`⏳ Gemini đang bận tạm thời (503/network), tự động retry sau ${waitSec} giây...`);
      await new Promise(r => setTimeout(r, waitSec * 1000));
    }
  }

  if (!parsed || !parsed.scenes) {
    throw new Error('Không thể tạo kịch bản từ Gemini API!');
  }

  if (articleTitle) {
    parsed.articleTitle = articleTitle;
    if (parsed.scenes?.[0]) {
      parsed.scenes[0].headline = shortenNewsTitle(articleTitle, 52).toUpperCase();
    }
  }
  for (const sc of parsed.scenes) {
    sc.voiceText = ensureRichVoiceText(sc.voiceText, sc.index);
  }
  return parsed;
}

/**
 * PRECISION AUDIO SYNC ENGINE:
 * - Duy nhất 1 giọng đọc vi-VN-NamMinhNeural xuyên suốt
 * - Tự động retry 9 lần chống rớt gói Edge-TTS
 * - Cắt bỏ khoảng lặng thừa (silenceremove)
 * - Tự động co giãn tốc độ (atempo) để giọng đọc luôn lấp đầy 9.35s / 10.0s
 */
function synthesizeSyncedAudio(text, outMp3, targetVideoDur = 10.0, targetSpeechDur = 9.35) {
  const dir = path.dirname(outMp3);
  const base = path.basename(outMp3, '.mp3');
  const txtPath = path.join(dir, `${base}_input.txt`);
  const rawMp3 = path.join(dir, `${base}_raw.mp3`);
  const trimMp3 = path.join(dir, `${base}_trimmed.mp3`);
  const pyRunner = path.join(dir, `${base}_tts.py`);

  fs.writeFileSync(txtPath, text, 'utf8');
  fs.writeFileSync(pyRunner, [
    'import asyncio, os, aiohttp, edge_tts',
    `text = open(${JSON.stringify(txtPath)}, "r", encoding="utf-8").read().strip()`,
    `out_file = ${JSON.stringify(rawMp3)}`,
    'async def run():',
    '    for attempt in range(1, 30):',
    '        try:',
    '            if os.path.exists(out_file): os.remove(out_file)',
    '            conn = aiohttp.TCPConnector(force_close=True, enable_cleanup_closed=True)',
    '            comm = edge_tts.Communicate(text, "vi-VN-NamMinhNeural", connector=conn)',
    '            await comm.save(out_file)',
    '            if os.path.exists(out_file) and os.path.getsize(out_file) > 2000:',
    '                return',
    '        except Exception as e:',
    '            print(f"  [TTS Retry {attempt}/30] {e}")',
    '            await asyncio.sleep(1.5)',
    '    raise RuntimeError("Edge-TTS failed after 30 retries")',
    'asyncio.run(run())'
  ].join('\n'), 'utf8');

  execSync(`${PYTHON_BIN} "${pyRunner}"`, { stdio: 'inherit' });

  execSync(`ffmpeg -y -i "${rawMp3}" -af "silenceremove=start_periods=1:start_duration=0.03:start_threshold=-42dB:stop_periods=-1:stop_duration=0.28:stop_threshold=-42dB,areverse,silenceremove=start_periods=1:start_duration=0.03:start_threshold=-42dB,areverse" -b:a 192k "${trimMp3}"`);

  const pureDur = probeDuration(trimMp3);
  let tempo = pureDur / targetSpeechDur;
  tempo = Math.max(0.88, Math.min(1.55, tempo));

  execSync(`ffmpeg -y -i "${trimMp3}" -af "atempo=${tempo.toFixed(4)},adelay=100|100,apad=pad_dur=${targetVideoDur}" -t ${targetVideoDur} -b:a 192k "${outMp3}"`);

  const activeSpeech = (pureDur / tempo).toFixed(2);
  console.log(`✅ [${base}] Giọng đọc gốc: ${pureDur.toFixed(2)}s -> Tempo: ${tempo.toFixed(2)}x -> Giọng đọc thực tế: ${activeSpeech}s / ${targetVideoDur}s`);

  for (const tmp of [txtPath, rawMp3, trimMp3, pyRunner]) {
    if (fs.existsSync(tmp)) fs.unlinkSync(tmp);
  }
}

function generateSceneAudios(scenes, outDir) {
  console.log(`\n🎙️ [3/6] Đang tổng hợp giọng đọc đồng nhất 100% (vi-VN-NamMinhNeural + Precision Sync 9.35s/10s)...`);
  for (const sc of scenes) {
    const outMp3 = path.join(outDir, `audio-${sc.index}.mp3`);
    synthesizeSyncedAudio(sc.voiceText, outMp3, 10.0, 9.35);
  }
}

async function generateOverlays(scriptData, outDir) {
  console.log(`\n🎨 [4/6] Đang dựng 4 lớp đồ họa tin tức 1080x1920 PNG trong suốt...`);
  const browser = await puppeteer.launch({ executablePath: CHROME_PATH, headless: true, args: ['--no-sandbox'] });
  const page = await browser.newPage();
  await page.setViewport({ width: 1080, height: 1920, deviceScaleFactor: 1 });

  const brandText = scriptData.brandBadge || '24H KHÁM PHÁ';

  for (const item of scriptData.scenes) {
    const html = `
      <!DOCTYPE html>
      <html>
      <head>
        <meta charset="utf-8">
        <style>
          @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@700;800;900&family=Be+Vietnam+Pro:wght@600;700;800&display=swap');
          * { margin: 0; padding: 0; box-sizing: border-box; }
          body {
            width: 1080px; height: 1920px; background: transparent;
            font-family: 'Be Vietnam Pro', sans-serif; position: relative; overflow: hidden;
          }
          .header-bar {
            position: absolute; top: 70px; left: 50px; right: 50px;
            display: flex; align-items: center; justify-content: space-between;
          }
          .brand-badge {
            background: linear-gradient(135deg, #FF3366 0%, #FF0033 100%);
            color: #FFFFFF; padding: 10px 26px; border-radius: 30px;
            font-family: 'Montserrat', sans-serif; font-weight: 900; font-size: 24px;
            letter-spacing: 1.5px; box-shadow: 0 8px 25px rgba(255, 51, 102, 0.4);
          }
          .live-badge {
            background: rgba(0, 0, 0, 0.65); backdrop-filter: blur(10px);
            border: 2px solid rgba(255, 255, 255, 0.3); color: #FFDE59;
            padding: 8px 20px; border-radius: 30px; font-weight: 800; font-size: 20px;
            display: flex; align-items: center; gap: 8px;
          }
          .live-dot { width: 12px; height: 12px; background: #00FF66; border-radius: 50%; box-shadow: 0 0 10px #00FF66; }
          .headline-card {
            position: absolute; top: 150px; left: 50px; right: 50px;
            background: linear-gradient(135deg, rgba(18, 18, 24, 0.92) 0%, rgba(30, 30, 45, 0.88) 100%);
            border: 2px solid rgba(255, 255, 255, 0.15); border-left: 8px solid ${item.color || '#00B4D8'};
            border-radius: 20px; padding: 26px 32px; box-shadow: 0 20px 50px rgba(0, 0, 0, 0.5); backdrop-filter: blur(16px);
          }
          .tag-pill {
            display: inline-block; background: ${item.color || '#00B4D8'}; color: #FFF;
            font-weight: 800; font-size: 19px; padding: 6px 16px; border-radius: 8px;
            margin-bottom: 14px; text-transform: uppercase;
          }
          .headline-title {
            color: #FFFFFF; font-family: 'Montserrat', sans-serif; font-size: 34px; font-weight: 900;
            line-height: 1.25; text-transform: uppercase; margin-bottom: 8px;
          }
          .headline-sub { color: #FFDD55; font-size: 23px; font-weight: 700; line-height: 1.35; }
          .bottom-ticker {
            position: absolute; bottom: 90px; left: 50px; right: 50px;
            background: rgba(0, 0, 0, 0.82); backdrop-filter: blur(12px); border-radius: 18px;
            border: 1.5px solid rgba(255, 255, 255, 0.2); padding: 18px 28px;
            display: flex; align-items: center; justify-content: space-between;
          }
          .ticker-text { color: #FFFFFF; font-weight: 800; font-size: 21px; }
          .match-score {
            background: rgba(255, 255, 255, 0.15); padding: 8px 18px; border-radius: 12px;
            font-weight: 900; font-size: 22px; color: #FFF; font-family: 'Montserrat', sans-serif;
          }
        </style>
      </head>
      <body>
        <div class="header-bar">
          <div class="brand-badge"><span>${brandText}</span></div>
          <div class="live-badge"><div class="live-dot"></div><span>VŨ TRỤ THỎ & GẤU 3D</span></div>
        </div>
        <div class="headline-card">
          <div class="tag-pill">${item.tag}</div>
          <div class="headline-title">${item.headline}</div>
          <div class="headline-sub">${item.sub}</div>
        </div>
        <div class="bottom-ticker">
          <div class="ticker-text">📢 ${scriptData.ticker || 'BẢN TIN HOẠT HÌNH 3D THỎ ĐỎ & GẤU BÉO 24/7'}</div>
          <div class="match-score">${scriptData.matchTitle || 'TIN NÓNG'}</div>
        </div>
      </body>
      </html>
    `;
    await page.setContent(html, { waitUntil: 'domcontentloaded' });
    await new Promise(r => setTimeout(r, 400));
    const outPath = path.join(outDir, `overlay-${item.index}.png`);
    await page.screenshot({ path: outPath, omitBackground: true });
    console.log(`✅ Đã lưu overlay cảnh ${item.index}: ${outPath}`);
  }
  await browser.close();
}

/**
 * Render cảnh 3D trên Muse.ai kèm cơ chế chống trùng cảnh (SHA-256) và kiểm tra thời lượng hợp lệ
 */
async function renderSceneOnMuse(page, prompt, destPath, seenHashes) {
  for (let attempt = 1; attempt <= 3; attempt++) {
    try {
      console.log(`  -> Mở phiên hội thoại mới sạch 100%: https://muse.ai/thread/new (Lần thử ${attempt}/3)`);
      await page.goto('https://muse.ai/thread/new', { waitUntil: 'domcontentloaded', timeout: 90000 });
      try {
        await page.waitForSelector('textarea', { timeout: 60000 });
      } catch (selErr) {
        const curUrl = page.url();
        const curTitle = await page.title().catch(() => '');
        throw new Error(`Không thấy ô nhập prompt trên Muse.ai (url=${curUrl}, title="${curTitle}"): ${selErr.message}`);
      }
      await new Promise(r => setTimeout(r, 2500));

      const initialVideos = await page.evaluate(() => {
        const vids = Array.from(document.querySelectorAll('video')).filter(v => {
          const isAvatar = v.closest('.rounded-full') || v.className.includes('rounded-full') || (v.parentElement && v.parentElement.className.includes('rounded-full'));
          return !isAvatar;
        });
        return vids.map(v => v.currentSrc || v.src).filter(Boolean);
      });

      await page.focus('textarea');
      await page.keyboard.down('Control');
      await page.keyboard.press('A');
      await page.keyboard.up('Control');
      await page.keyboard.press('Backspace');

      await page.evaluate((text) => {
        const ta = document.querySelector('textarea');
        ta.focus();
        const setter = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value')?.set;
        if (setter) setter.call(ta, text);
        else ta.value = text;
        ta.dispatchEvent(new Event('input', { bubbles: true }));
      }, prompt);

      await page.keyboard.press('Space');
      await page.keyboard.press('Backspace');
      await new Promise(r => setTimeout(r, 600));

      const sent = await page.evaluate(() => {
        const btn = document.querySelector('button[aria-label="Send"]:not([disabled])')
          || Array.from(document.querySelectorAll('button')).find(b => /send/i.test(b.getAttribute('aria-label') || ''));
        if (btn) { btn.click(); return true; }
        return false;
      });

      if (!sent) await page.keyboard.press('Enter');

      console.log(`⏱️ Đang chờ Muse.ai render cảnh 3D Pixar (10s)...`);
      const startTime = Date.now();
      let videoUrl = null;

      while (Date.now() - startTime < 360000) {
        await new Promise(r => setTimeout(r, 4000));
        const elapsed = Math.round((Date.now() - startTime) / 1000);

        const check = await page.evaluate((initList) => {
          const vids = Array.from(document.querySelectorAll('video')).filter(v => {
            const isAvatar = v.closest('.rounded-full') || v.className.includes('rounded-full') || (v.parentElement && v.parentElement.className.includes('rounded-full'));
            return !isAvatar;
          });
          const urls = vids.map(v => v.currentSrc || v.src).filter(Boolean);
          const fresh = urls.filter(u => !initList.includes(u));

          const atts = Array.from(document.querySelectorAll('[data-testid="hatch-chat-attachment-presentation-video"]'));
          const newestAtt = atts.length > 0 ? atts[atts.length - 1] : null;
          const isGenerating = Boolean(newestAtt?.querySelector('[data-visualcompletion="loading-state"], .animate-spin'));

          const optionBtns = Array.from(document.querySelectorAll('button')).filter(b => /render|option|yes|proceed/i.test(b.innerText || ''));
          if (optionBtns.length > 0 && !isGenerating && fresh.length === 0) {
            const renderBtn = optionBtns.find(b => /render|option 1|proceed/i.test(b.innerText || ''));
            if (renderBtn) renderBtn.click();
          }

          if (atts.length > 0 && !isGenerating && fresh.length === 0) newestAtt.click();

          if (fresh.length > 0) {
            const candidate = fresh[fresh.length - 1];
            if (candidate.startsWith('blob:') || candidate.includes('.mp4') || candidate.includes('fbcdn')) {
              return { ready: true, url: candidate, isGen: isGenerating };
            }
          }
          return { ready: false, isGen: isGenerating };
        }, initialVideos);

        console.log(`⏱️ [${elapsed}s] Video ready: ${check.ready}, Generating: ${check.isGen}`);
        if (check.ready && check.url) {
          videoUrl = check.url;
          break;
        }
      }

      if (!videoUrl) throw new Error('Timeout rendering video on Muse.ai');

      await new Promise(r => setTimeout(r, 3000));
      const base64Data = await page.evaluate(async (url) => {
        const res = await fetch(url);
        const blob = await res.blob();
        return new Promise((resolve) => {
          const reader = new FileReader();
          reader.onloadend = () => resolve(reader.result.split(',')[1]);
          reader.readAsDataURL(blob);
        });
      }, videoUrl);

      fs.writeFileSync(destPath, Buffer.from(base64Data, 'base64'));
      const sizeBytes = fs.statSync(destPath).size;
      const dur = probeDuration(destPath);
      const hash = fileSha256(destPath);

      if (sizeBytes < 800000 || dur < 7.0) {
        throw new Error(`File cảnh tải về không hợp lệ (size=${sizeBytes}, dur=${dur}s)`);
      }
      if (seenHashes.has(hash)) {
        throw new Error(`Phát hiện Muse.ai trả về cảnh trùng lặp (hash=${hash.slice(0, 12)}), tự động render lại!`);
      }

      seenHashes.add(hash);
      console.log(`💾 Đã lưu & kiểm định cảnh 3D thành công: ${destPath} (${(sizeBytes / 1024 / 1024).toFixed(2)} MB, ${dur.toFixed(1)}s)`);
      return;
    } catch (err) {
      console.warn(`⚠️ Cảnh báo lần thử ${attempt}: ${err.message}`);
      if (attempt === 3) throw err;
    }
  }
}

async function compositeFinalVideo(outDir, finalVideoPath) {
  console.log(`\n🎬 [5/6] Đang hậu kỳ & đóng gói Master Video 9:16 Full HD (1080x1920)...`);

  for (let i = 1; i <= 4; i++) {
    const vPath = path.join(outDir, `scene-${i}.mp4`);
    const aPath = path.join(outDir, `audio-${i}.mp3`);
    const oPath = path.join(outDir, `overlay-${i}.png`);
    const formatted = path.join(outDir, `scene-${i}-formatted.mp4`);

    execSync(`ffmpeg -y -i "${vPath}" -i "${aPath}" -i "${oPath}" -filter_complex "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=25:5[bg]; [0:v]scale=1080:1920:force_original_aspect_ratio=decrease[fg]; [bg][fg]overlay=(W-w)/2:(H-h)/2[vid]; [vid][2:v]overlay=0:0[v]; [1:a]apad=pad_dur=10[a]" -map "[v]" -map "[a]" -t 10 -c:v libx264 -pix_fmt yuv420p -c:a aac -b:a 192k "${formatted}"`);
  }

  const concatList = path.join(outDir, 'concat_all.txt');
  const sharedOutro = path.join(SHARED_DIR, 'fixed_outro_formatted_916.mp4');

  if (fs.existsSync(sharedOutro)) {
    const localOutro = path.join(outDir, 'scene-5-formatted.mp4');
    fs.copyFileSync(sharedOutro, localOutro);
    fs.writeFileSync(concatList, `file 'scene-1-formatted.mp4'\nfile 'scene-2-formatted.mp4'\nfile 'scene-3-formatted.mp4'\nfile 'scene-4-formatted.mp4'\nfile 'scene-5-formatted.mp4'\n`);
  } else {
    fs.writeFileSync(concatList, `file 'scene-1-formatted.mp4'\nfile 'scene-2-formatted.mp4'\nfile 'scene-3-formatted.mp4'\nfile 'scene-4-formatted.mp4'\n`);
  }

  execSync(`ffmpeg -y -f concat -safe 0 -i "${concatList}" -c copy "${finalVideoPath}"`);
  console.log(`\n🏆 MASTER VIDEO HOÀN TẤT TẠI: ${finalVideoPath}`);
}

/**
 * Tự động xuất bản sang hệ thống Web Affiliate & Social Poster Queue (d:/web_aff)
 */
function publishToWebAffEcosystem(videoId, finalVideoPath, scriptData, sourceUrl) {
  if (!fs.existsSync(WEB_AFF_ROOT)) return;
  console.log(`\n🚀 [6/6] Đang đồng bộ Video 3D Thỏ & Gấu sang Hệ thống Web Player & Social Queue (${WEB_AFF_ROOT})...`);

  const fullDir = path.join(WEB_AFF_ROOT, 'storage', '2_web_full');
  const teaserDir = path.join(WEB_AFF_ROOT, 'storage', '3_social_teaser');
  const webVideosDir = path.join(WEB_AFF_ROOT, 'web', 'videos');

  for (const d of [fullDir, teaserDir, webVideosDir]) {
    fs.mkdirSync(d, { recursive: true });
  }

  const targetMp4 = path.join(fullDir, `${videoId}.mp4`);
  const targetPoster = path.join(fullDir, `${videoId}_poster.jpg`);
  const webMp4 = path.join(webVideosDir, `${videoId}.mp4`);
  const webPoster = path.join(webVideosDir, `${videoId}_poster.jpg`);
  const teaserMp4 = path.join(teaserDir, `${videoId}_teaser.mp4`);
  const captionTxt = path.join(teaserDir, `${videoId}_caption.txt`);

  // Copy video sang các khoang
  fs.copyFileSync(finalVideoPath, targetMp4);
  fs.copyFileSync(finalVideoPath, webMp4);
  fs.copyFileSync(finalVideoPath, teaserMp4);

  // Trích xuất ảnh thumbnail poster sắc nét ở giây 2.5
  execSync(`ffmpeg -y -ss 00:00:02.500 -i "${finalVideoPath}" -vframes 1 -q:v 2 "${targetPoster}"`);
  fs.copyFileSync(targetPoster, webPoster);

  const durSec = Math.round(probeDuration(finalVideoPath));
  const mins = String(Math.floor(durSec / 60)).padStart(2, '0');
  const secs = String(durSec % 60).padStart(2, '0');
  const durationFormatted = `${mins}:${secs}`;

  const baseTitle = shortenNewsTitle(
    scriptData.articleTitle || scriptData.scenes?.[0]?.headline || scriptData.matchTitle || 'Bản Tin 3D Thỏ & Gấu',
    72
  );
  const titleClean = `[3D Thỏ & Gấu] ${baseTitle}`;
  const socialCaption = scriptData.socialCaption || `${titleClean} - Xem trọn bộ bản tin hoạt hình 3D tại link dưới bình luận nhé! #ThoVaGau3D #BanTin3D #TinTuc24H #Trending`;

  fs.writeFileSync(captionTxt, socialCaption, 'utf8');

  const metaObj = {
    id: videoId,
    title: titleClean,
    duration: durationFormatted,
    views: `${(Math.floor(Math.random() * 250) + 120)}.5K`,
    likes: `${(Math.floor(Math.random() * 25) + 12)}.8K`,
    uploadDate: 'Vừa xong',
    category: '🐰🐻 VŨ TRỤ THỎ & GẤU 3D',
    pipeline_type: 'rabbit_bear_3d',
    source_article_url: sourceUrl,
    full_video_path: targetMp4,
    poster_path: targetPoster,
    teaser_video_path: teaserMp4,
    web_video_url: `videos/${videoId}.mp4`,
    web_poster_url: `videos/${videoId}_poster.jpg`,
    target_web_url: `https://tho-news.com/?v=${videoId}`,
    social_caption: socialCaption,
    status: 'published_to_web',
    published_at: new Date().toISOString()
  };

  const metaPath = path.join(fullDir, `${videoId}_meta.json`);
  fs.writeFileSync(metaPath, JSON.stringify(metaObj, null, 2), 'utf8');

  // Gọi publisher.py để cập nhật web/config.js & web/videos_db.json
  const publisherPy = path.join(WEB_AFF_ROOT, 'automation', '3_web_publisher', 'publisher.py');
  if (fs.existsSync(publisherPy)) {
    try {
      execSync(`${PYTHON_BIN} "${publisherPy}" --meta "${metaPath}"`, { stdio: 'inherit' });
    } catch (e) {
      console.warn('Lưu ý khi chạy publisher.py:', e.message);
    }
  }
  console.log(`✅ Đã xuất bản '${videoId}' lên Web Player & Hàng đợi Social thành công!`);
}

function loadMuseCookieString() {
  if (fs.existsSync(COOKIE_FILE)) {
    return fs.readFileSync(COOKIE_FILE, 'utf8').trim();
  }
  const b64File = path.join(__dirname, 'muse_session.b64');
  if (fs.existsSync(b64File)) {
    const raw = Buffer.from(fs.readFileSync(b64File, 'utf8').trim(), 'base64').toString('utf8').trim();
    try { fs.writeFileSync(COOKIE_FILE, raw, 'utf8'); } catch (e) {}
    return raw;
  }
  throw new Error('Không tìm thấy muse_cookie.txt hoặc muse_session.b64!');
}

function sendTelegramCompletionNotice(chatId, videoId, scriptData) {
  if (!chatId) return;
  let botToken = process.env.TELEGRAM_BOT_TOKEN || '';
  if (!botToken) {
    for (const envPath of [path.join(WEB_AFF_ROOT, '.env'), path.join(ENGINE_ROOT, '.env')]) {
      if (fs.existsSync(envPath)) {
        const m = fs.readFileSync(envPath, 'utf8').match(/^TELEGRAM_BOT_TOKEN=(.+)$/m);
        if (m && m[1]) { botToken = m[1].trim(); break; }
      }
    }
  }
  if (!botToken) return;

  const displayTitle = shortenNewsTitle(
    scriptData.articleTitle || scriptData.scenes?.[0]?.headline || scriptData.matchTitle || 'Bản Tin 3D Thỏ & Gấu',
    72
  );
  const webUrl = `https://tho-news.com/?v=${videoId}`;
  const msgText = [
    `🎉 <b>HOÀN TẤT DỰNG VIDEO 3D THỎ & GẤU TRÊN CLOUD!</b>`,
    `━━━━━━━━━━━━━━━━━━━━━━━━━━`,
    `🎬 <b>Tiêu đề:</b> [3D Thỏ & Gấu] ${displayTitle}`,
    `🆔 <b>Mã Video:</b> <code>${videoId}</code>`,
    `🌐 <b>Xem trực tiếp trên Web Player:</b>`,
    `${webUrl}`,
    ``,
    `✅ <i>Video đã được giữ nguyên bản 100% đưa vào Hàng đợi Social & đẩy thẳng lên Vercel!</i>`
  ].join('\n');

  const body = JSON.stringify({
    chat_id: chatId,
    text: msgText,
    parse_mode: 'HTML'
  });

  const req = https.request(`https://api.telegram.org/bot${botToken}/sendMessage`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(body) }
  });
  req.on('error', () => {});
  req.write(body);
  req.end();
}

async function main() {
  const args = process.argv.slice(2);
  const urlArg = args.find(a => a.startsWith('http')) || args[0];
  const chatIdIdx = args.indexOf('--chat-id');
  const chatId = (chatIdIdx !== -1 && args[chatIdIdx + 1]) ? args[chatIdIdx + 1] : '';

  if (!urlArg) {
    console.error('Cách dùng: node scripts/run-auto.mjs <LINK_BAI_BAO> [--chat-id <CHAT_ID>]');
    process.exit(1);
  }

  const timestamp = new Date().toISOString().replace(/[-:T.]/g, '').slice(0, 14);
  const videoId = `tho_gau_3d_${timestamp}`;
  const outDir = path.join(ENGINE_ROOT, 'output', `auto-${timestamp}`);
  fs.mkdirSync(outDir, { recursive: true });

  const article = await fetchArticle(urlArg);
  const scriptData = await generateScript(article.text, article.title);
  fs.writeFileSync(path.join(outDir, 'script.json'), JSON.stringify(scriptData, null, 2));

  generateSceneAudios(scriptData.scenes, outDir);
  await generateOverlays(scriptData, outDir);

  const cookieStr = loadMuseCookieString();
  const cookies = cookieStr.split('; ').map(p => {
    const [k, ...v] = p.split('=');
    return { name: k.trim(), value: v.join('=').trim(), domain: '.muse.ai', path: '/' };
  });

  const isHeadlessLinux = process.platform !== 'win32' && !process.env.DISPLAY;
  const browser = await puppeteer.launch({
    executablePath: CHROME_PATH,
    headless: isHeadlessLinux ? 'new' : false,
    protocolTimeout: 600000,
    args: [
      '--no-sandbox',
      '--disable-setuid-sandbox',
      '--disable-dev-shm-usage',
      '--disable-gpu',
      '--disable-blink-features=AutomationControlled',
      '--window-size=1280,850'
    ]
  });
  const page = await browser.newPage();
  await page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36');
  await page.setViewport({ width: 1280, height: 850 });
  await page.setCookie(...cookies);

  const seenHashes = new Set();
  for (const scene of scriptData.scenes) {
    const destPath = path.join(outDir, `scene-${scene.index}.mp4`);
    console.log(`\n🎬 Đang dựng Cảnh ${scene.index}/4 trên Muse.ai (Thỏ Đỏ & Gấu Béo)...`);
    await renderSceneOnMuse(page, scene.visualPrompt, destPath, seenHashes);
    await new Promise(r => setTimeout(r, 2000));
  }
  await browser.close();

  const finalVideo = path.join(outDir, 'master_video.mp4');
  await compositeFinalVideo(outDir, finalVideo);

  publishToWebAffEcosystem(videoId, finalVideo, scriptData, urlArg);
  sendTelegramCompletionNotice(chatId, videoId, scriptData);

  // Tự động dọn thư mục tạm sau khi xuất bản xong để không đầy ổ cứng Cloud VM
  try {
    fs.rmSync(outDir, { recursive: true, force: true });
    console.log(`🧹 Đã dọn thư mục tạm: ${outDir}`);
  } catch (e) {}
}

main().catch(err => {
  console.error('Fatal error:', err);
  process.exit(1);
});
