import fs from "node:fs/promises";

const JOKES_URL = "https://readme-jokes.vercel.app/api?hideBorder&";
const CAPSULE_PREFIX = "https://capsule-render.vercel.app/api?type=waving&color=gradient&customColorList=6,11,20&height=100&section=footer&text=";
const CAPSULE_SUFFIX = "&fontSize=16&fontColor=ffffff&animation=twinkling";

function extractQAFromSvg(svg) {
    // The jokes API uses foreignObject with HTML content, not SVG text elements
    // Look for question and answer in <p> tags with classes "question" and "answer"

    const questionMatch = svg.match(/<p[^>]*class="question"[^>]*><b>Q\.<\/b>\s*([^<]+)<\/p>/i);
    const answerMatch = svg.match(/<p[^>]*class="answer"[^>]*><b>A\.<\/b>\s*([^<]+)<\/p>/i);

    if (!questionMatch || !answerMatch) {
        // Fallback: try to extract any Q./A. pattern from the SVG
        const qMatch = svg.match(/<b>Q\.<\/b>\s*([^<]+)/i);
        const aMatch = svg.match(/<b>A\.<\/b>\s*([^<]+)/i);

        if (qMatch && aMatch) {
            return {
                q: qMatch[1].trim(),
                a: aMatch[1].trim()
            };
        }
        return null;
    }

    return {
        q: questionMatch[1].trim(),
        a: answerMatch[1].trim()
    };
}

function buildCapsuleUrl(q, a) {
    // Keep it single line and not too long
    const line = `${q} — ${a}`.replace(/\s+/g, " ").trim().slice(0, 180);
    const encoded = encodeURIComponent(line);
    return `${CAPSULE_PREFIX}${encoded}${CAPSULE_SUFFIX}`;
}

async function main() {
    try {
        console.log("Fetching joke from API...");
        const svg = await fetch(JOKES_URL, { headers: { "User-Agent": "footer-updater" } }).then(r => r.text());

        console.log("Extracting Q&A from SVG...");
        const qa = extractQAFromSvg(svg);

        let newImg;
        if (!qa) {
            console.log("Could not extract Q&A from joke SVG. Using fallback footer.");
            newImg = `<img src="https://capsule-render.vercel.app/api?type=waving&color=gradient&customColorList=6,11,20&height=100&section=footer&text=Ship%20small%2C%20ship%20often%20%E2%80%94%20see%20you%20in%20the%20next%20commit!&fontSize=16&fontColor=ffffff&animation=twinkling" alt="Footer"/>`;
        } else {
            console.log(`Found Q&A: "${qa.q}" — "${qa.a}"`);
            newImg = `<img src="${buildCapsuleUrl(qa.q, qa.a)}" alt="Footer"/>`;
        }
        const readmePath = "./README.md";
        let readme = await fs.readFile(readmePath, "utf8");

        // Replace the line inside the FOOTER block
        const updated = readme.replace(
            /(<!--\s*FOOTER_START\s*-->)[\s\S]*?(<!--\s*FOOTER_END\s*-->)/,
            `$1\n<div align="center">\n  ${newImg}\n</div>\n$2`
        );

        if (updated !== readme) {
            await fs.writeFile(readmePath, updated, "utf8");
            console.log("README footer updated with latest joke Q&A.");
        } else {
            console.log("No footer block found or no change necessary.");
        }
    } catch (error) {
        console.error("Error updating footer:", error);
        process.exit(1);
    }
}

await main();