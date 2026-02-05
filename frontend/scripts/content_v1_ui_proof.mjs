import fs from "node:fs";
import path from "node:path";
import puppeteer from "puppeteer-core";

const ROOT = path.resolve(process.cwd(), "..");
const ARTIFACT_ROOT = path.join(ROOT, "artifacts", "proof");
const stamp = new Date().toISOString().replace(/[:.]/g, "-");
const outDir = path.join(ARTIFACT_ROOT, `content-v1-live-${stamp}`);
fs.mkdirSync(outDir, { recursive: true });

const APP_BASE = process.env.APP_BASE || "http://localhost:3000";
const AUTH_BASE = process.env.AUTH_BASE || "http://localhost:8003";
const DASH_BASE = process.env.DASH_BASE || "http://localhost:8000";

const testEmail = `qa.contentv1.${Date.now()}@example.com`;
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
  return { status: res.status, text, json: text ? JSON.parse(text) : {} };
}

async function signupOrLogin() {
  const signup = await api("POST", `${AUTH_BASE}/auth/signup`, {
    email: testEmail,
    password: testPassword,
    name: "QA Content V1",
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
  if (start.status !== 200) {
    return;
  }
  const payload = start.json || {};
  const questions = payload.questions || [];
  if (!questions.length) {
    return;
  }
  const answers = questions.map((q) => ({
    question_id: q?.dash_metadata?.dash_question_id,
    skill_id: q?.dash_metadata?.skill_ids?.[0] || "",
    is_correct: true,
  })).filter((a) => a.question_id && a.skill_id);
  if (!answers.length) return;
  await api("POST", `${DASH_BASE}/assessment/complete`, { subject: "math", answers }, token);
}

async function wait(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function clickButtonByText(page, text) {
  const clicked = await page.evaluate((label) => {
    const buttons = Array.from(document.querySelectorAll("button"));
    const target = buttons.find((b) =>
      (b.textContent || "").toUpperCase().includes(label.toUpperCase()),
    );
    if (!target) return false;
    target.click();
    return true;
  }, text);
  if (!clicked) {
    throw new Error(`Button not found: ${text}`);
  }
}

async function run() {
  const auth = await signupOrLogin();
  const token = auth.token;
  await ensureAssessmentComplete(token);

  const browser = await puppeteer.launch({
    executablePath: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    headless: true,
    args: ["--window-size=1600,1000"],
    defaultViewport: { width: 1600, height: 1000 },
  });

  const page = await browser.newPage();
  page.setDefaultTimeout(60000);

  await page.goto(`${APP_BASE}/app/login`, { waitUntil: "networkidle2" });
  await page.screenshot({ path: path.join(outDir, "01-login.png"), fullPage: true });
  const emailInput = await page.$('input[type="email"], input[placeholder*="email" i]');
  const passwordInput = await page.$('input[type="password"]');
  if (emailInput && passwordInput) {
    await emailInput.click({ clickCount: 3 });
    await page.keyboard.press("Backspace");
    await emailInput.type(testEmail);
    await passwordInput.click({ clickCount: 3 });
    await page.keyboard.press("Backspace");
    await passwordInput.type(testPassword);
  }
  await page.screenshot({ path: path.join(outDir, "02-login-filled.png"), fullPage: true });

  // Deterministic auth: write JWT directly, then open app.
  await page.goto(`${APP_BASE}/`, { waitUntil: "networkidle2" });
  await page.evaluate((jwt) => {
    localStorage.setItem("jwt_token", jwt);
    sessionStorage.setItem("onboarding_complete", "true");
  }, token);
  await page.goto(`${APP_BASE}/app`, { waitUntil: "networkidle2" });
  await page.waitForFunction(
    () => (document.body?.innerText || "").toUpperCase().includes("BUILD YOUR LEARNING JOURNEY"),
    { timeout: 90000 },
  );
  await page.screenshot({ path: path.join(outDir, "03-contentv1-onboarding.png"), fullPage: true });

  // Fill onboarding.
  const ageInput = await page.$('input[type="number"]');
  const goalInput = await page.$('input[placeholder*="world history" i]');
  if (!ageInput || !goalInput) {
    throw new Error("Content V1 onboarding inputs not found");
  }
  await ageInput.click({ clickCount: 3 });
  await page.keyboard.press("Backspace");
  await ageInput.type("12");
  await goalInput.click({ clickCount: 3 });
  await page.keyboard.press("Backspace");
  await goalInput.type("python programming and world history");
  await page.screenshot({ path: path.join(outDir, "04-contentv1-onboarding-filled.png"), fullPage: true });

  await clickButtonByText(page, "Create Plan");

  await page.waitForFunction(
    () => (document.body?.innerText || "").toUpperCase().includes("SUBMIT"),
    { timeout: 120000 },
  );
  await page.screenshot({ path: path.join(outDir, "05-contentv1-question-1.png"), fullPage: true });

  await clickButtonByText(page, "Submit");
  await wait(2000);
  await page.screenshot({ path: path.join(outDir, "06-contentv1-after-submit.png"), fullPage: true });

  await clickButtonByText(page, "Next");
  await wait(2500);
  await page.screenshot({ path: path.join(outDir, "07-contentv1-next.png"), fullPage: true });

  const profileId = await page.evaluate(() => localStorage.getItem("content_v1_profile_id"));
  const planRes = profileId
    ? await api("GET", `${DASH_BASE}/api/content-v1/plan?learner_profile_id=${encodeURIComponent(profileId)}`, null, token)
    : null;

  await browser.close();

  const evidence = {
    created_at: new Date().toISOString(),
    app_base: APP_BASE,
    auth_base: AUTH_BASE,
    dash_base: DASH_BASE,
    auth_email: testEmail,
    profile_id: profileId,
    endpoints: {
      onboarding: `${DASH_BASE}/api/content-v1/onboarding`,
      next: `${DASH_BASE}/api/content-v1/questions/next`,
      submit: `${DASH_BASE}/api/content-v1/questions/submit`,
      plan: `${DASH_BASE}/api/content-v1/plan`,
    },
    plan_snapshot: planRes?.json || null,
    screenshots: [
      "01-login.png",
      "02-login-filled.png",
      "03-contentv1-onboarding.png",
      "04-contentv1-onboarding-filled.png",
      "05-contentv1-question-1.png",
      "06-contentv1-after-submit.png",
      "07-contentv1-next.png",
    ],
  };
  fs.writeFileSync(path.join(outDir, "evidence.json"), JSON.stringify(evidence, null, 2));
  console.log(outDir);
}

run().catch((err) => {
  console.error(err);
  process.exit(1);
});
