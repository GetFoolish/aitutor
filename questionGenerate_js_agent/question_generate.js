const fs = require("fs");
const path = require("path");
const genAI = require("@google/genai");
const axios = require("axios"); // Add axios for API calls
const { BlobServiceClient } = require("@azure/storage-blob");
const sharp = require("sharp"); // Added sharp for post-process resizing

const blobService = BlobServiceClient.fromConnectionString(
  process.env.AZURE_STORAGE_CONNECTION_STRING
);


const folderPath = "./filtered_files";
const outputFolder = "./new_questions";

// API endpoints
const API_BASE_URL = "http://localhost:8001/api";
const GET_QUESTION_URL = `${API_BASE_URL}/get-question-for-generation`;
const SAVE_QUESTION_URL = `${API_BASE_URL}/save-generated-question`;

if (!fs.existsSync(outputFolder)) {
  fs.mkdirSync(outputFolder);
}

const promptTemplate = `
we need to regenerate the questions in a new way but the structure must remain the same.
You can change the values.

We are using images and widgets, so please add detailed alt texts suitable for image-generation prompts.
Do not add any extra unnecessary information. Here is the JSON file; rewrite it in a new way.

If the JSON has choices questions, then you can add an "alt" key inside their objects.

Always make sure alt text is based on the exact requirement — it should guide the AI clearly on what type of image to generate.
You can add more detailed alt text because these are image prompts for AI, so make them richer and more descriptive.

Do thorough research and create high-quality image-generation prompts that clearly help the AI understand what kind of image to produce.

Please also modify the questions slightly — create new variations but keep the structure exactly the same.

Make sure image size should be **256x256** for all images.

The images are appearing too large, so ensure that image descriptions always reflect accurate proportions based on the required size.

{{json}}
`;

// Fetch question from API
async function fetchQuestionFromAPI() {
  try {
    console.log("Fetching question from API...");
    const response = await axios.get(GET_QUESTION_URL);
    const question = response.data;

    if (question && question.question) {
      const sourceQuestionId = question._id;
      delete question._id;
      console.log(`Fetched question ID: ${sourceQuestionId}`);
      return { sourceQuestionId, questionData: question };
    }
    return null;
  } catch (error) {
    console.error("Failed to fetch question from API:", error.message);
    return null;
  }
}

// Save generated question to API
async function saveQuestionToAPI(sourceQuestionId, generatedData) {
  try {
    const url = `${SAVE_QUESTION_URL}/${sourceQuestionId}`;
    console.log(`Saving generated question to API for ID: ${sourceQuestionId}`);

    const response = await axios.post(url, generatedData, {
      headers: { "Content-Type": "application/json" },
    });

    console.log(`✅ Question saved successfully. Status: ${response.status}`);
    return response.data;
  } catch (error) {
    console.error("Failed to save question to API:", error.message);
    if (error.response) {
      console.error(
        "API Response:",
        error.response.status,
        error.response.data
      );
    }
    throw error;
  }
}

// Replace images with generated ones
async function replaceImageUrlsWithGeneratedImages(
  obj,
  containerName = "inventory"
) {
  if (Array.isArray(obj)) {
    return Promise.all(
      obj.map((item) =>
        replaceImageUrlsWithGeneratedImages(item, containerName)
      )
    );
  } else if (typeof obj === "object" && obj !== null) {
    const newObj = {};

    for (const key in obj) {
      if (key === "content" && obj.images) {
        let contentStr = obj.content;

        for (const url in obj.images) {
          if (contentStr.includes(url) && obj.images[url].alt) {
            const prompt = obj.images[url].alt;

            // Generate image
            const buffer = await generateImageWithGemini(prompt);

            // Upload to Azure
            const blobName = `${Date.now()}-${Math.random()}.png`;
            const azureUrl = await uploadBufferToAzure(
              containerName,
              blobName,
              buffer
            );

            contentStr = contentStr.split(url).join(azureUrl);
          }
        }

        newObj[key] = contentStr;
      } else if (key === "content" && obj.alt) {
        let contentStr = obj[key];

        const markdownImgRegex = /!\[(.*?)\]\((web\+graphie:\/\/.*?)\)/g;
        let match;

        while ((match = markdownImgRegex.exec(contentStr)) !== null) {
          const graphieUrl = match[2];
          const altText = obj.alt;

          const buffer = await generateImageWithGemini(altText);

          const blobName = `${Date.now()}-${Math.random()}.png`;
          const azureUrl = await uploadBufferToAzure(
            containerName,
            blobName,
            buffer
          );

          contentStr = contentStr.replace(graphieUrl, azureUrl);
        }

        newObj[key] = contentStr;
        continue;
      } else if (key === "backgroundImage" && obj[key].url && obj.alt) {
        const buffer = await generateImageWithGemini(obj.alt);
        const blobName = `${Date.now()}-${Math.random()}.png`;
        const azureUrl = await uploadBufferToAzure(
          containerName,
          blobName,
          buffer
        );
        newObj[key] = { ...obj[key], url: azureUrl };
      } else if (key === "imageUrl" && obj.imageAlt) {
        const buffer = await generateImageWithGemini(obj.imageAlt);
        const blobName = `${Date.now()}-${Math.random()}.png`;
        const azureUrl = await uploadBufferToAzure(
          containerName,
          blobName,
          buffer
        );
        newObj[key] = azureUrl;
      } else {
        newObj[key] = await replaceImageUrlsWithGeneratedImages(
          obj[key],
          containerName
        );
      }
    }

    return newObj;
  }

  return obj;
}

// Main loop
async function main() {
  const MAX_QUESTIONS = 10;
  let processed = 0;

  while (processed < MAX_QUESTIONS) {
    console.log(`\n▶️ Fetching question ${processed + 1} of ${MAX_QUESTIONS}`);

    const fetchedQuestion = await fetchQuestionFromAPI();

    if (!fetchedQuestion || !fetchedQuestion.questionData) {
      console.log("❌ No more questions available from API.");
      break;
    }

    const questionJSON = JSON.stringify(fetchedQuestion.questionData, null, 2);

    if (questionJSON.includes("https") || questionJSON.includes("web+")) {
      console.log("✔️ Valid question found, processing...");
      await processQuestionFromAPI(fetchedQuestion);
      processed++;
    } else {
      console.log("⚠️ Invalid question (no image links), skipping...");
      continue;
    }

    await new Promise((res) => setTimeout(res, 1500));
  }

  console.log(`\n🎉 DONE! Processed ${processed} questions.`);
}

// Process API question
async function processQuestionFromAPI(fetchedQuestion) {
  const { sourceQuestionId, questionData } = fetchedQuestion;

  try {
    const questionJSON = JSON.stringify(questionData, null, 2);
    const prompt = promptTemplate.replace("{{json}}", questionJSON);

    console.log("Generating new question...");
    const responseText = await generateJSONWithAI(prompt);

    const cleaned = responseText
      .replace(/```json/gi, "")
      .replace(/```/g, "")
      .trim();

    let parsed;
    try {
      parsed = JSON.parse(cleaned);
      console.log(`Generated valid JSON`);

      const newdata = await replaceImageUrlsWithGeneratedImages(parsed);

      await saveQuestionToAPI(sourceQuestionId, newdata);

      const outputPath = path.join(
        outputFolder,
        `question_${sourceQuestionId}.json`
      );
      fs.writeFileSync(outputPath, JSON.stringify(newdata, null, 2));
      console.log(`Local backup saved: ${outputPath}`);
    } catch (e) {
      console.error(`Invalid JSON generated:`, e.message);
      console.error("AI Output:\n", cleaned);
    }
  } catch (err) {
    console.error(`Error processing question ${sourceQuestionId}:`, err);
  }
}

// Local file processing
async function processLocalFiles() {
  fs.readdir(folderPath, async (err, files) => {
    if (err) return console.error("Error reading folder:", err);
    if (!files.length) return console.log("No files found in folder.");

    for (const file of files) {
      const filePath = path.join(folderPath, file);

      try {
        const data = fs.readFileSync(filePath, "utf8");
        const prompt = promptTemplate.replace("{{json}}", data);

        const responseText = await generateJSONWithAI(prompt);

        const cleaned = responseText
          .replace(/```json/gi, "")
          .replace(/```/g, "")
          .trim();

        let parsed;
        try {
          parsed = JSON.parse(cleaned);
          console.log(`VALID JSON — PROCESSING FILE: ${file}`);
          const newdata = await replaceImageUrlsWithGeneratedImages(parsed);
          const outputPath = path.join(outputFolder, file);
          fs.writeFileSync(outputPath, JSON.stringify(newdata, null, 2));
        } catch (e) {
          console.error(`INVALID JSON — SKIPPING FILE: ${file}`);
          console.error("Error:", e.message);
          console.error("AI Output:\n", cleaned);
          continue;
        }
      } catch (err) {
        console.error(`Error processing file: ${file}`, err);
      }
    }

    console.log("\nAll files processed.");
  });
}

// Generate JSON with AI
const generateJSONWithAI = async (prompt) => {
  const ai = new genAI.GoogleGenAI({
    apiKey: process.env.GOOGLE_API_KEY,
  });
  const response = await ai.models.generateContent({
    model: "gemini-2.5-flash",
    contents: prompt,
  });

  return await response.text;
};

async function generateImageWithGemini(promptText) {
  try {
    const ai = new genAI.GoogleGenAI({
      apiKey: process.env.GOOGLE_API_KEY,
    });
    const response = await ai.models.generateContent({
      model: "gemini-3-pro-image-preview",
      contents: [
        {
          role: "user",
          parts: [
            {
              text: `${promptText}. Image size: 256x256 pixels, high quality, detailed.`,
            },
          ],
        },
      ],
    });

    const candidate = response?.candidates?.[0];
    if (candidate?.content?.parts) {
      for (const part of candidate.content.parts) {
        if (part.inlineData && part.inlineData.data) {
          let buffer = Buffer.from(part.inlineData.data, "base64");

          // Post-process with sharp
          buffer = await sharp(buffer).resize(256, 256).png().toBuffer();
          return buffer;
        }
      }
    }
    throw new Error(
      "No inline image data returned. Model might have returned text only."
    );
  } catch (err) {
    throw new Error(`Gemini Image Gen failed: ${err.message}`);
  }
}

// Upload buffer to Azure
async function uploadBufferToAzure(containerName, blobName, buffer) {
  try {
    const containerClient = blobService.getContainerClient(containerName);
    if (!(await containerClient.exists())) await containerClient.create();

    const blockBlobClient = containerClient.getBlockBlobClient(blobName);
    await blockBlobClient.uploadData(buffer, {
      blobHTTPHeaders: { blobContentType: "image/png" },
    });
    return blockBlobClient.url;
  } catch (err) {
    throw new Error(`Azure upload failed: ${err.message}`);
  }
}

// Run main
main();
