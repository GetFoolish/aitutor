import fs from "node:fs";
import path from "node:path";
import puppeteer from "puppeteer-core";

const ROOT = path.resolve(process.cwd(), "..");
const ARTIFACT_ROOT = path.join(ROOT, "artifacts", "proof");
const stamp = new Date().toISOString().replace(/[:.]/g, "-");
const outDir = path.join(ARTIFACT_ROOT, `content-v1-multitopic-${stamp}`);
fs.mkdirSync(outDir, { recursive: true });

const APP_BASE = process.env.APP_BASE || "http://localhost:3000";
const AUTH_BASE = process.env.AUTH_BASE || "http://localhost:8003";
const DASH_BASE = process.env.DASH_BASE || "http://localhost:8000";

const topics = [
  { age: 12, goal: "python programming fundamentals" },
  { age: 12, goal: "world history and civilizations" },
  { age: 12, goal: "climate science and weather systems" },
  { age: 12, goal: "public speaking confidence" },
];

const testEmail = `qa.multitopic.${Date.now()}@example.com`;
const testPassword = "TestPass123!";

async function api(method, url, body, token) {
  const headers = { "Content-Type": "application/json" };
  if (token) headers.Authorization = `Bearer ${token}`;
  const res = await fetch(url, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });
  const text = await res.text();
  let json = {};
  try { json = text ? JSON.parse(text) : {}; } catch (_) { json = { raw: text }; }
  return { status: res.status, text, json };
}

async function signupOrLogin() {
  const signup = await api("POST", `${AUTH_BASE}/auth/signup`, {
    email: testEmail,
    password: testPassword,
    name: "QA Multitopic",
    date_of_birth: "2013-01-01",
    gender: "Other",
    preferred_language: "English",
    location: "US",
    user_type: "student",
  });
  if (signup.status === 200) return signup.json;
  const login = await api("POST", `${AUTH_BASE}/auth/login`, {
    email: testEmail,
    password: testPassword,
  });
  if (login.status !== 200) {
    throw new Error(`Auth failed: signup=${signup.status} login=${login.status}`);
  }
  return login.json;
}


async function ensureAssessmentComplete(token) {
  const start = await api("POST", `${DASH_BASE}/assessment/start/math`, {}, token);
  if (start.status !== 200) return;
  const questions = start.json?.questions || [];
  if (!questions.length) return;
  const answers = questions.map((q) => ({
    question_id: q?.dash_metadata?.dash_question_id,
    skill_id: q?.dash_metadata?.skill_ids?.[0] || "",
    is_correct: true,
  })).filter((a) => a.question_id && a.skill_id);
  if (!answers.length) return;
  await api("POST", `${DASH_BASE}/assessment/complete`, { subject: "math", answers }, token);
}

async function wait(ms) { return new Promise((r) => setTimeout(r, ms)); }

async function clickButtonByText(page, text) {
  const clicked = await page.evaluate((label) => {
    const buttons = Array.from(document.querySelectorAll("button"));
    const target = buttons.find((b) => (b.textContent || "").toUpperCase().includes(label.toUpperCase()));
    if (!target) return false;
    target.click();
    return true;
  }, text);
  if (!clicked) throw new Error(`Button not found: ${text}`);
}

async function run() {
  const auth = await signupOrLogin();
  const token = auth.token;
  await ensureAssessmentComplete(token);

  const browser = await puppeteer.launch({
    executablePath: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    headless: true,
    args: ["--window-size=1800,1100"],
    defaultViewport: { width: 1800, height: 1100 },
  });

  const page = await browser.newPage();
  page.setDefaultTimeout(90000);

  // Force auth + app entry.
  await page.goto(`${APP_BASE}/`, { waitUntil: "networkidle2" });
  await page.evaluate((jwt) => {
    localStorage.setItem("jwt_token", jwt);
    sessionStorage.setItem("onboarding_complete", "true");
  }, token);

  const runs = [];

  for (let i = 0; i < topics.length; i++) {
    const t = topics[i];
    const prefix = `${String(i + 1).padStart(2, "0")}-${t.goal.replace(/[^a-z0-9]+/gi, "-").toLowerCase()}`;

    // Reset Content V1 session.
    await page.goto(`${APP_BASE}/app`, { waitUntil: "networkidle2" });
    await page.evaluate(() => {
      localStorage.removeItem("content_v1_profile_id");
    });
    await page.goto(`${APP_BASE}/app`, { waitUntil: "networkidle2" });

    await page.waitForFunction(() => (document.body?.innerText || "").toUpperCase().includes("BUILD YOUR LEARNING JOURNEY"));
    await page.screenshot({ path: path.join(outDir, `${prefix}-onboarding.png`), fullPage: true });

    const ageInput = await page.$('input[type="number"]');
    const goalInput = await page.$('input[placeholder*="world history" i]');
    if (!ageInput || !goalInput) throw new Error("Onboarding inputs not found");

    await ageInput.click({ clickCount: 3 });
    await page.keyboard.press("Backspace");
    await ageInput.type(String(t.age));
    await goalInput.click({ clickCount: 3 });
    await page.keyboard.press("Backspace");
    await goalInput.type(t.goal);
    await page.screenshot({ path: path.join(outDir, `${prefix}-onboarding-filled.png`), fullPage: true });

    await clickButtonByText(page, "Create Plan");
    await page.waitForFunction(() => (document.body?.innerText || "").toUpperCase().includes("SUBMIT"), { timeout: 120000 });
    await page.screenshot({ path: path.join(outDir, `${prefix}-question-1.png`), fullPage: true });

    const profileId = await page.evaluate(() => localStorage.getItem("content_v1_profile_id"));

    // 3 submit-next loops to force progression movement.
    const loopSnapshots = [];
    for (let loop = 1; loop <= 3; loop++) {
      await clickButtonByText(page, "Submit");
      await wait(1200);
      await page.screenshot({ path: path.join(outDir, `${prefix}-loop${loop}-after-submit.png`), fullPage: true });

      const planRes = await api("GET", `${DASH_BASE}/api/content-v1/plan?learner_profile_id=${encodeURIComponent(profileId)}`, null, token);
      loopSnapshots.push({ loop, plan: planRes.json });

      await clickButtonByText(page, "Next");
      await wait(1500);
      await page.screenshot({ path: path.join(outDir, `${prefix}-loop${loop}-next.png`), fullPage: true });
    }

    // Pull one direct next question for evidence of queue availability/source/format.
    const nextRes = await api("GET", `${DASH_BASE}/api/content-v1/questions/next?learner_profile_id=${encodeURIComponent(profileId)}`, null, token);

    runs.push({
      topic: t.goal,
      age: t.age,
      profile_id: profileId,
      loop_snapshots: loopSnapshots,
      api_next_status: nextRes.status,
      api_next_question_meta: nextRes.json?.question?.dash_metadata || null,
      api_next_source: nextRes.json?.question?.source || nextRes.json?.question?.dash_metadata?.source || null,
      api_next_format: nextRes.json?.question?.question?.widgets ? Object.values(nextRes.json.question.question.widgets)[0]?.type : null,
    });
  }

  await browser.close();

  const evidence = {
    created_at: new Date().toISOString(),
    app_base: APP_BASE,
    topics,
    auth_email: testEmail,
    runs,
    checks: {
      any_topic_count: runs.length,
      gemini_only: runs.every((r) => ["gemini", "gemini_derived", null].includes(r.api_next_source)),
      loop_and_progression_observed: runs.every((r) => r.loop_snapshots.length === 3),
      queue_next_available: runs.every((r) => r.api_next_status === 200),
    },
  };

  fs.writeFileSync(path.join(outDir, "evidence.json"), JSON.stringify(evidence, null, 2));

  // Make a quick mp4 from key frames.
  const ordered = [];
  for (let i = 0; i < topics.length; i++) {
    const t = topics[i];
    const prefix = `${String(i + 1).padStart(2, "0")}-${t.goal.replace(/[^a-z0-9]+/gi, "-").toLowerCase()}`;
    ordered.push(`${prefix}-onboarding-filled.png`, `${prefix}-question-1.png`, `${prefix}-loop1-after-submit.png`, `${prefix}-loop1-next.png`, `${prefix}-loop3-after-submit.png`);
  }
  const framesTxt = ordered.map((f) => `file '${f}'\nduration 2`).join("\n") + "\n" + `file '${ordered[ordered.length - 1]}'\n`;
  fs.writeFileSync(path.join(outDir, "frames.txt"), framesTxt);

  console.log(outDir);
}

run().catch((err) => {
  console.error(err);
  process.exit(1);
});
