
// Simplified mock for marked if not available
let marked;
try {
    marked = require('marked');
} catch (e) {
    marked = {
        parse: (text) => text // Just return text if marked is missing
    };
}

// Mock KaTeX
const katex = {
    renderToString: (math, options) => {
        return `<span class="katex">${math}</span>`;
    }
};

// --- COPY OF ContentRendererUtils logic ---

const katexOptions = {
    throwOnError: false,
    output: 'html',
};

const cleanLegacyContent = (text) => {
    let processedText = text;
    // 1. Remove stray blockquote markers ">"
    processedText = processedText.replace(/([\|\n]|^)\s*>+\s*/gm, '$1');
    // 2. Handle headers
    processedText = processedText.replace(/(\s+)>+(#{1,6}|!\[)/g, '$1$2');
    processedText = processedText.replace(/(^|[\n|])\s*(#{1,6})\s*([^#|\n]+?)\s*#*\s*(?=[\|\n]|$)/g, '$1\n\n$2 $3\n\n');
    // 3. Unescape escaped dollar signs
    processedText = processedText.replace(/\\(\$)/g, '&dollar;');
    // 4. Normalize legacy double-pipe
    processedText = processedText.replace(/\s*\|\|\s*/g, '\n\n');
    // 5. Cleanup
    processedText = processedText.replace(/(^|\n)([0-9]+\.\s+)/gm, '$1\n$2');
    processedText = processedText.replace(/^\|\s*$/gm, '');
    processedText = processedText.replace(/^[\s\-:|]+$/gm, '');
    processedText = processedText.replace(/^[-:|]+\|[-:|]+$/gm, '');
    processedText = processedText.replace(/^\|([^|]*?)$/gm, '$1');
    processedText = processedText.replace(/\|=/g, '=');
    processedText = processedText.replace(/^\s*\|\s*$/gm, '');
    processedText = processedText.replace(/\s*\|\s*$/gm, '');
    processedText = processedText.replace(/(Step\s*\d+)\|\s*/gi, '$1 ');
    processedText = processedText.replace(/^\|(\d)/gm, '$1');
    processedText = processedText.replace(/\|\s*×/g, '×');
    return processedText;
};

const renderMath = (text) => {
    return `<span class="math">${text}</span>`;
};

const processTable = (text) => text;

const preprocessCodeBlocks = (text) => text;
const processImageMarkdown = (text) => text;
const preprocessMarkdown = (text) => {
    let processed = text;
    processed = processed.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    return processed;
};

const processContent = (content) => {
    console.log('--- START ---');
    console.log('Original:', JSON.stringify(content));

    // Phase 1
    let processed = cleanLegacyContent(content);
    console.log('Phase 1 (Clean):', JSON.stringify(processed));

    // Phase 2
    const mathBlocks = [];
    processed = processed.replace(/\$\$([\s\S]+?)\$\$|\$([^$]+)\$/g, (match) => {
        const placeholder = `__ATHENA_MATH_RAW_${mathBlocks.length}__`;
        mathBlocks.push(match);
        return placeholder;
    });
    console.log('Phase 2 (Protect Math):', JSON.stringify(processed));
    console.log('Math Blocks:', JSON.stringify(mathBlocks));

    // Phase 3
    processed = processTable(processed);

    // Phase 3.5
    if (processed.includes('&dollar;') || processed.includes('{,}')) {
        processed = processed.replace(/&dollar;/g, '$');
        processed = processed.replace(/\{,\}/g, ',');
    }
    console.log('Phase 3.5 (Decode Entities):', JSON.stringify(processed));

    // Phase 6
    const htmlProtected = [];
    const addProtection = (html) => {
        const placeholder = `ATHENAHTMLSAFE${htmlProtected.length}ENDMARKER`;
        htmlProtected.push(html);
        return placeholder;
    };

    mathBlocks.forEach((math, idx) => {
        // In real code, math is rendered by renderMath
        const renderedMath = renderMath(math);
        const protectedPlaceholder = addProtection(renderedMath);
        processed = processed.replace(`__ATHENA_MATH_RAW_${idx}__`, protectedPlaceholder);
    });
    console.log('Phase 6 (Render Math):', JSON.stringify(processed));

    // Phase 7, 8
    processed = processed.replace(/\[\[☃\s+([^\]]+)\]\]/g, (_, widgetId) => {
        const html = `<span class="widget">${widgetId.trim()}</span>`;
        return addProtection(html);
    });
    console.log('Phase 8 (Widgets):', JSON.stringify(processed));

    // Phase 8.5
    processed = preprocessMarkdown(processed);
    console.log('Phase 8.5 (Markdown):', JSON.stringify(processed));

    // Phase 9
    let finalHtml = marked.parse(processed);
    console.log('Phase 9 (Marked):', JSON.stringify(finalHtml));

    // Phase 10
    console.log('Protected Count:', htmlProtected.length);
    for (let idx = htmlProtected.length - 1; idx >= 0; idx--) {
        const html = htmlProtected[idx];
        const placeholder = `ATHENAHTMLSAFE${idx}ENDMARKER`;
        console.log(`Restoring ${idx}: ${placeholder} -> ${html}`);
        finalHtml = finalHtml.split(placeholder).join(html);
    }
    console.log('Phase 10 (Restore):', JSON.stringify(finalHtml));

    return finalHtml;
};

const testContent = `A \\$10$ pack of juice boxes contains $24$ individual juice bottles.

**What is the cost per bottle?**
*Round your answer to the nearest whole cent.*

\\$$ [[☃ numeric-input 1]]`;

processContent(testContent);
