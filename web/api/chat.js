/**
 * Serverless chat & grounded retrieval API for Groww SIP Retention Discovery Engine.
 *
 * Implements:
 * 1. Keyword/TF-IDF retrieval over web/data/corpus.json (top 5 relevant records).
 * 2. Optional Groq AI synthesis (GROQ_API_KEY, GROQ_MODEL, 10s timeout, error-safe).
 * 3. Offline retrieval fallback with exact badge text:
 *    - "GROUNDED IN CORPUS - LIVE AI ANSWER"
 *    - "GROUNDED IN CORPUS - OFFLINE RETRIEVAL (no live AI)"
 * 4. Transparent provenance: Record IDs, source labels, verbatim quotes,
 *    and clear split between "what customers said" and "interpretation".
 * 5. Guardrails: No investment advice, no causation claims, out-of-corpus detection,
 *    insufficient evidence warnings, and zero developer-reply leakage.
 */

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

// Helper to load .env variables if not already set in process.env
function ensureEnvLoaded() {
  if (process.env.GROQ_API_KEY && (process.env.GROQ_MODEL || process.env.LLM_MODEL)) {
    return;
  }
  const rootEnvPath = path.resolve(fileURLToPath(new URL('../../.env', import.meta.url)));
  if (fs.existsSync(rootEnvPath)) {
    try {
      const content = fs.readFileSync(rootEnvPath, 'utf8');
      for (const line of content.split(/\r?\n/)) {
        const trimmed = line.trim();
        if (!trimmed || trimmed.startsWith('#') || !trimmed.includes('=')) continue;
        const [k, ...vParts] = trimmed.split('=');
        const key = k.trim();
        const val = vParts.join('=').trim().replace(/^["']|["']$/g, '');
        if (!process.env[key]) {
          process.env[key] = val;
        }
      }
    } catch (_) {}
  }
}
ensureEnvLoaded();

// Exact Badge Constants
export const BADGE_LIVE = 'GROUNDED IN CORPUS - LIVE AI ANSWER';
export const BADGE_OFFLINE = 'GROUNDED IN CORPUS - OFFLINE RETRIEVAL (no live AI)';

// Out of corpus regex pattern (F&O, derivatives, crypto, intraday trading)
export const OUT_OF_CORPUS_REGEX = /\b(f&o|fno|futures|options?|derivatives?|intraday|call\s+option|put\s+option|strike\s+price|expiry|crypto|cryptocurrency|bitcoin|ethereum|forex)\b/i;

// Standard English stop words
const STOP_WORDS = new Set([
  'a', 'about', 'above', 'after', 'again', 'against', 'all', 'am', 'an', 'and', 'any', 'are', 'aren\'t',
  'as', 'at', 'be', 'because', 'been', 'before', 'being', 'below', 'between', 'both', 'but', 'by',
  'can', 'can\'t', 'cannot', 'could', 'couldn\'t', 'did', 'didn\'t', 'do', 'does', 'doesn\'t', 'doing',
  'don\'t', 'down', 'during', 'each', 'few', 'for', 'from', 'further', 'had', 'hadn\'t', 'has', 'hasn\'t',
  'have', 'haven\'t', 'having', 'he', 'he\'d', 'he\'ll', 'he\'s', 'her', 'here', 'here\'s', 'hers',
  'herself', 'him', 'himself', 'his', 'how', 'how\'s', 'i', 'i\'d', 'i\'ll', 'i\'m', 'i\'ve', 'if',
  'in', 'into', 'is', 'isn\'t', 'it', 'it\'s', 'its', 'itself', 'let\'s', 'me', 'more', 'most',
  'mustn\'t', 'my', 'myself', 'no', 'nor', 'not', 'of', 'off', 'on', 'once', 'only', 'or', 'other',
  'ought', 'our', 'ours', 'ourselves', 'out', 'over', 'own', 'same', 'shan\'t', 'she', 'she\'d', 'she\'ll',
  'she\'s', 'should', 'shouldn\'t', 'so', 'some', 'such', 'than', 'that', 'that\'s', 'the', 'their',
  'theirs', 'them', 'themselves', 'then', 'there', 'there\'s', 'these', 'they', 'they\'d', 'they\'ll',
  'they\'re', 'they\'ve', 'this', 'those', 'through', 'to', 'too', 'under', 'until', 'up', 'very',
  'was', 'wasn\'t', 'we', 'we\'d', 'we\'ll', 'we\'re', 'we\'ve', 'were', 'weren\'t', 'what', 'what\'s',
  'when', 'when\'s', 'where', 'where\'s', 'which', 'while', 'who', 'who\'s', 'whom', 'why', 'why\'s',
  'with', 'won\'t', 'would', 'wouldn\'t', 'you', 'you\'d', 'you\'ll', 'you\'re', 'you\'ve', 'your', 'yours',
]);

/**
 * Normalize and stem a word token for resilient retrieval.
 */
export function normalizeToken(word) {
  let token = word.toLowerCase().trim().replace(/^[^\w]+|[^\w]+$/g, '');
  if (!token) return '';

  // Domain-specific normalizations
  if (/^sip('?s)?$/.test(token)) return 'sip';
  if (/^auto[- ]?pay(s)?$/.test(token)) return 'autopay';
  if (/^auto[- ]?debit(s)?$/.test(token)) return 'autodebit';
  if (/^mandate('?s)?$/.test(token)) return 'mandate';
  if (/^pause[sd]?|pausing$/.test(token)) return 'pause';
  if (/^stop[s]?|stopped|stopping$/.test(token)) return 'stop';
  if (/^reduce[sd]?|reducing|reduction$/.test(token)) return 'reduce';
  if (/^continue[sd]?|continuing|continuation$/.test(token)) return 'continue';
  if (/^charge[sd]?|charging$/.test(token)) return 'charge';
  if (/^load[sd]?|exit[- ]?load$/.test(token)) return 'exitload';
  if (/^fail[s]?|failed|failing|failure[s]?$/.test(token)) return 'fail';
  if (/^support[s]?|customer[- ]?care$/.test(token)) return 'support';
  if (/^ticket[s]?$/.test(token)) return 'ticket';
  if (/^delay[sd]?|delayed|delaying$/.test(token)) return 'delay';
  if (/^volatil(e|ity)|crash[es]?|drawdown[s]?$/.test(token)) return 'volatility';
  if (/^bank[s]?|allotment[s]?|nav$/.test(token)) return token;

  // General English suffix stemming
  token = token.replace(/(ing|tion|ment|ness|less|ed|es|s)$/, '');
  return token;
}

/**
 * Tokenize string into meaningful normalized tokens.
 */
export function tokenizeText(text) {
  if (!text || typeof text !== 'string') return [];
  const words = text.toLowerCase().split(/[\s,.;:!?()\[\]{}"'\/\-_]+/);
  const tokens = [];
  for (const w of words) {
    if (!w || STOP_WORDS.has(w)) continue;
    const norm = normalizeToken(w);
    if (norm && norm.length >= 2 && !STOP_WORDS.has(norm)) {
      tokens.push(norm);
    }
  }
  return tokens;
}

/**
 * Load corpus records from disk.
 */
let cachedCorpus = null;
export function loadCorpusData() {
  if (cachedCorpus) return cachedCorpus;

  const candidatePaths = [
    fileURLToPath(new URL('../data/corpus.json', import.meta.url)),
    path.resolve(process.cwd(), 'web/data/corpus.json'),
    path.resolve(process.cwd(), 'data/corpus.json'),
  ];

  for (const p of candidatePaths) {
    if (fs.existsSync(p)) {
      try {
        const raw = fs.readFileSync(p, 'utf-8');
        cachedCorpus = JSON.parse(raw);
        return cachedCorpus;
      } catch (err) {
        console.error(`Failed to parse corpus from ${p}:`, err);
      }
    }
  }

  throw new Error('Could not find web/data/corpus.json. Please run scripts/export_dashboard_data.py first.');
}

/**
 * Keyword & TF-IDF relevance retriever over the 203 mutual fund records.
 * Returns the top 5 records with relevance scores.
 */
export function retrieveRelevantRecords(query, corpus, options = {}) {
  const records = corpus?.records || [];
  const topK = options.topK || 5;

  if (!query || typeof query !== 'string' || !query.trim()) {
    return {
      query: '',
      records: [],
      is_low_evidence: true,
      is_out_of_corpus: false,
      top_score: 0,
    };
  }

  const queryTrimmed = query.trim();
  const isOutOfCorpus = OUT_OF_CORPUS_REGEX.test(queryTrimmed);
  const queryTokens = tokenizeText(queryTrimmed);

  if (queryTokens.length === 0) {
    return {
      query: queryTrimmed,
      records: [],
      is_low_evidence: true,
      is_out_of_corpus: isOutOfCorpus,
      top_score: 0,
    };
  }

  // Precompute document frequencies across all records
  const docFreq = new Map();
  const docTokensMap = new Map();

  for (const rec of records) {
    const combinedText = `${rec.text} ${rec.primary_theme} ${rec.secondary_theme || ''} ${rec.sip_behavior}`;
    const tokens = tokenizeText(combinedText);
    docTokensMap.set(rec.feedback_id, tokens);
    const uniqueTokens = new Set(tokens);
    for (const t of uniqueTokens) {
      docFreq.set(t, (docFreq.get(t) || 0) + 1);
    }
  }

  const N = records.length;
  const scoredRecords = [];

  for (const rec of records) {
    const tokens = docTokensMap.get(rec.feedback_id) || [];
    if (tokens.length === 0) continue;

    // Term frequencies in this document
    const termFreq = new Map();
    for (const t of tokens) {
      termFreq.set(t, (termFreq.get(t) || 0) + 1);
    }

    let docScore = 0;
    let matchedTokensCount = 0;

    for (const qToken of queryTokens) {
      const tf = termFreq.get(qToken) || 0;
      if (tf > 0) {
        matchedTokensCount += 1;
        const df = docFreq.get(qToken) || 1;
        // Standard smooth IDF
        const idf = Math.log((N + 1) / (df + 1)) + 1.0;
        // Sub-linear term frequency scaling
        const tfScaled = 1 + Math.log(tf);

        let weight = tfScaled * idf;

        // Domain boosts
        if (['pause', 'stop', 'reduce', 'continue', 'mandate', 'autopay', 'exitload', 'support'].includes(qToken)) {
          weight *= 1.5;
        }

        // Extra boost if query token appears in primary theme
        if (rec.primary_theme.toLowerCase().includes(qToken)) {
          weight *= 1.4;
        }

        docScore += weight;
      }
    }

    if (docScore > 0) {
      // Normalize by sqrt of document length to prevent long reviews from dominating
      const lengthPenalty = Math.sqrt(tokens.length + 5);
      const normalizedScore = (docScore / lengthPenalty) * (1 + matchedTokensCount * 0.2);

      scoredRecords.push({
        ...rec,
        relevance_score: Number(normalizedScore.toFixed(3)),
        matched_tokens_count: matchedTokensCount,
      });
    }
  }

  // Sort descending by relevance score
  scoredRecords.sort((a, b) => b.relevance_score - a.relevance_score);
  const topRecords = scoredRecords.slice(0, topK);
  const topScore = topRecords.length > 0 ? topRecords[0].relevance_score : 0;

  // Determine low evidence: if score is very low or fewer than 2 matched terms
  const isLowEvidence = topScore < 0.35 || topRecords.length === 0;

  return {
    query: queryTrimmed,
    records: topRecords,
    is_low_evidence: isLowEvidence,
    is_out_of_corpus: isOutOfCorpus,
    top_score: topScore,
  };
}

/**
 * Format prompt for Groq containing ONLY redacted user text from retrieved records.
 * STRICT PRIVACY: Zero developer replies, zero PII.
 */
export function buildPrompt(query, records) {
  const contextExcerpts = records.map((r, i) => {
    return `[Record ${i + 1}] ID: ${r.feedback_id} | Source: ${r.source_display || r.source} | Theme: ${r.primary_theme} | Stated SIP Behavior: ${r.sip_behavior}\nText: "${r.text}"`;
  }).join('\n\n');

  return {
    systemPrompt: `You are a research synthesis assistant for the Groww Mutual Fund SIP Retention Discovery Engine.
Your job is to answer user inquiries strictly grounded in the provided customer feedback excerpts.

NON-NEGOTIABLE RULES:
1. ONLY use the feedback records provided below. Do not invent facts, quotes, numbers, or customer experiences.
2. Structure your response into two distinct, labelled sections separated by a horizontal rule:
   ### What Customers Said
   (Quote verbatim phrases from the records with their exact feedback IDs and sources. State the exact customer sentiment and specific issues mentioned.)
   
   ---
   
   ### Synthesis & Interpretation
   (Synthesize patterns across the feedback. State clearly that theme mentions indicate reported customer friction, not proof of systemic platform failure or guaranteed causation. Do NOT provide investment advice, do NOT recommend specific mutual funds or stocks, and do NOT extrapolate beyond retail mutual fund SIP behavior.)
3. If the retrieved records offer insufficient context to answer the question, state clearly in both sections: "Insufficient evidence in corpus to draw a firm conclusion."
4. If the query asks about derivatives, F&O, crypto, or day trading, note that the discovery corpus strictly evaluates mutual fund SIP retention and contains no F&O data.`,
    userPrompt: `User Query: "${query}"

Retrieved Customer Feedback Records (N=${records.length}):
${contextExcerpts}

Please provide your grounded synthesis following the exact two-part format:`,
  };
}

/**
 * Server-side Groq API caller with 10s timeout and complete exception safety.
 */
export async function queryGroq(apiKey, model, promptPayload, options = {}) {
  const timeoutMs = options.timeoutMs || 10000;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  const modelToUse = model || process.env.GROQ_MODEL || process.env.LLM_MODEL || 'openai/gpt-oss-120b';

  try {
    const res = await fetch('https://api.groq.com/openai/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${apiKey.trim()}`,
      },
      body: JSON.stringify({
        model: modelToUse,
        messages: [
          { role: 'system', content: promptPayload.systemPrompt },
          { role: 'user', content: promptPayload.userPrompt },
        ],
        temperature: 0.1,
        max_tokens: 800,
      }),
      signal: controller.signal,
    });

    clearTimeout(timer);

    if (!res.ok) {
      const errText = await res.text().catch(() => '');
      throw new Error(`Groq API returned HTTP ${res.status}: ${errText.slice(0, 200)}`);
    }

    const data = await res.json();
    const content = data.choices?.[0]?.message?.content || '';
    if (!content.trim()) {
      throw new Error('Empty response content received from Groq.');
    }

    return {
      success: true,
      content: content.trim(),
      model: modelToUse,
    };
  } catch (err) {
    clearTimeout(timer);
    let statusMatch = err.message && err.message.match(/HTTP (\d{3})/);
    let fallbackMsg = 'API request failed';
    if (err.name === 'AbortError' || err.message?.includes('timed out')) {
      fallbackMsg = 'timeout';
    } else if (statusMatch) {
      fallbackMsg = `Groq returned HTTP ${statusMatch[1]}`;
    }
    return {
      success: false,
      error: fallbackMsg,
      fallback_reason: fallbackMsg,
      model: modelToUse,
    };
  }
}

/**
 * Deterministic offline retrieval synthesis when Groq is unavailable or key is missing.
 */
export function generateOfflineAnswer(query, retrievalResult) {
  const { records, is_low_evidence, is_out_of_corpus } = retrievalResult;

  if (is_out_of_corpus) {
    const whatCustomersSaid = `The query "${query}" asks about topics (such as Futures & Options, derivatives, day trading, or crypto) that are outside the mutual fund SIP discovery corpus. The dataset strictly evaluates retail mutual fund and platform retention feedback and contains zero records on F&O or crypto trading.`;
    const interpretation = `No mutual fund SIP retention conclusions can be drawn for out-of-scope assets. Mutual fund investors operate on multi-month SIP investment horizons, whereas derivatives represent short-term leveraged trading with fundamentally different retention dynamics.`;

    return {
      what_customers_said: whatCustomersSaid,
      interpretation: interpretation,
      full_text: `### What Customers Said\n${whatCustomersSaid}\n\n---\n\n### Synthesis & Interpretation\n${interpretation}`,
    };
  }

  if (is_low_evidence || records.length === 0) {
    const whatCustomersSaid = `Insufficient evidence: Few or no mutual fund feedback records in the 203-record corpus closely match the inquiry "${query}".`;
    const interpretation = `Because this topic has low representation in the audited corpus, drawing conclusions would risk extrapolation bias. Further targeted user discovery or larger survey cohorts are recommended to evaluate this specific area.`;

    return {
      what_customers_said: whatCustomersSaid,
      interpretation: interpretation,
      full_text: `### What Customers Said\n${whatCustomersSaid}\n\n---\n\n### Synthesis & Interpretation\n${interpretation}`,
    };
  }

  // Build authentic customer evidence summary
  const quoteLines = records.map((r, idx) => {
    const excerpt = r.text.length > 200 ? `${r.text.slice(0, 197)}...` : r.text;
    const behaviorInfo = r.sip_behavior !== 'unspecified' ? ` [Reported behavior: ${r.sip_behavior}]` : '';
    return `${idx + 1}. **${r.feedback_id}** (${r.source_display}): "${excerpt}"${behaviorInfo}`;
  });

  const whatCustomersSaid = `Based on ${records.length} retrieved feedback records matching "${query}":\n\n` + quoteLines.join('\n\n');

  // Synthesize common themes represented
  const themeCounts = {};
  for (const r of records) {
    themeCounts[r.primary_theme] = (themeCounts[r.primary_theme] || 0) + 1;
  }
  const topThemesStr = Object.entries(themeCounts)
    .map(([theme, count]) => `${theme} (${count} record${count > 1 ? 's' : ''})`)
    .join(', ');

  const interpretation = `**Corpus Friction Signals:** The matched feedback centers primarily on ${topThemesStr}.\n\n` +
    `*Methodological Context:* Customer feedback highlights perceived friction points (e.g. mandate setup hurdles, customer service turnaround, or market anxiety). These mentions reflect subjective user experiences and should not be treated as proof of single-variable churn causation. No investment advice or fund recommendations are provided.`;

  return {
    what_customers_said: whatCustomersSaid,
    interpretation: interpretation,
    full_text: `### What Customers Said\n${whatCustomersSaid}\n\n---\n\n### Synthesis & Interpretation\n${interpretation}`,
  };
}

/**
 * Validate that every card the AI returned only cites record IDs that were
 * actually retrieved, and that each card cites at least one record.
 * Returns true when all cards pass, false otherwise.
 */
export function validateCards(cards, retrievedIds) {
  if (!Array.isArray(cards) || cards.length === 0) return false;
  const idSet = new Set(retrievedIds);
  for (const c of cards) {
    if (!c || typeof c.title !== 'string' || typeof c.sentence !== 'string') return false;
    if (!Array.isArray(c.record_ids) || c.record_ids.length === 0) return false;
    for (const id of c.record_ids) {
      if (!idSet.has(id)) return false;
    }
  }
  return true;
}

/**
 * Build offline summary cards grouped by primary_theme (top 2–3 themes).
 * Returns array of {title, sentence, record_ids} with no generated prose.
 */
export function buildOfflineCards(records) {
  const themeMap = {};
  for (const r of records) {
    const t = r.primary_theme || 'Unknown';
    if (!themeMap[t]) themeMap[t] = [];
    themeMap[t].push(r.feedback_id);
  }
  return Object.entries(themeMap)
    .sort((a, b) => b[1].length - a[1].length)
    .slice(0, 3)
    .map(([theme, ids]) => ({
      title: theme,
      sentence: `${ids.length} record${ids.length > 1 ? 's' : ''}`,
      record_ids: ids,
    }));
}

/**
 * Split raw markdown response into what_customers_said and interpretation sections.
 */
export function parseSections(rawText) {
  const parts = rawText.split(/---|\bSynthesis & Interpretation\b/i);
  if (parts.length >= 2) {
    let part1 = parts[0].replace(/###?\s*What Customers Said/i, '').trim();
    let part2 = parts.slice(1).join('\n').replace(/###?\s*Synthesis & Interpretation/i, '').trim();
    return {
      what_customers_said: part1,
      interpretation: part2,
      full_text: rawText,
    };
  }
  return {
    what_customers_said: rawText,
    interpretation: 'Note: Qualitative synthesis grounded in retrieved corpus records.',
    full_text: rawText,
  };
}

/**
 * End-to-end chat response coordinator.
 */
export async function generateChatResponse(query, options = {}) {
  const corpus = options.corpus || loadCorpusData();
  const apiKey = (options.apiKey !== undefined ? options.apiKey : process.env.GROQ_API_KEY) || '';
  const model = options.model !== undefined ? options.model : (process.env.GROQ_MODEL || process.env.LLM_MODEL || 'openai/gpt-oss-120b');

  const retrievalResult = retrieveRelevantRecords(query, corpus, options);

  // If query is out of corpus or low evidence, use grounded disclaimer logic
  if (retrievalResult.is_out_of_corpus || retrievalResult.is_low_evidence) {
    const offlineAns = generateOfflineAnswer(query, retrievalResult);
    return {
      mode: 'offline',
      badge: BADGE_OFFLINE,
      fallback_reason: retrievalResult.is_out_of_corpus ? 'out of corpus query' : 'low evidence in corpus',
      query: retrievalResult.query,
      records_retrieved: retrievalResult.records.length,
      records: retrievalResult.records,
      answer: offlineAns,
      is_low_evidence: retrievalResult.is_low_evidence,
      is_out_of_corpus: retrievalResult.is_out_of_corpus,
      model_used: 'none (offline-retrieval)',
    };
  }

  // Determine fallback reason if going offline
  let fallbackReason = options.fallback_reason || '';
  if (!apiKey.trim()) {
    fallbackReason = 'no key set';
  } else if (!model || !model.trim()) {
    fallbackReason = 'model name not set';
  }

  // If GROQ_API_KEY is present, attempt live AI synthesis
  if (apiKey.trim()) {
    if (!model || !model.trim()) {
      fallbackReason = 'model name not set';
    } else {
      const promptPayload = buildPrompt(query, retrievalResult.records);
      const groqResult = await queryGroq(apiKey, model, promptPayload, options);

      if (groqResult.success) {
        let cards = null;
        // Try parsing JSON cards if present in response or content
        try {
          const jsonMatch = groqResult.content.match(/```json\s*([\s\S]*?)\s*```/) || groqResult.content.match(/(\[\s*\{[\s\S]*\}\s*\])/);
          if (jsonMatch) {
            const parsedCards = JSON.parse(jsonMatch[1]);
            const retrievedIds = retrievalResult.records.map(r => r.feedback_id);
            if (validateCards(parsedCards, retrievedIds)) {
              cards = parsedCards;
            }
          }
        } catch (e) {
          cards = null;
        }

        if (!cards) {
          cards = buildOfflineCards(retrievalResult.records);
        }

        const parsed = parseSections(groqResult.content);
        parsed.cards = cards;

        return {
          mode: 'live',
          badge: BADGE_LIVE,
          query: retrievalResult.query,
          records_retrieved: retrievalResult.records.length,
          records: retrievalResult.records,
          answer: parsed,
          is_low_evidence: false,
          is_out_of_corpus: false,
          model_used: groqResult.model,
        };
      } else {
        fallbackReason = groqResult.fallback_reason || groqResult.error || 'Groq call failed';
        console.warn('Groq call failed, falling back to offline retrieval:', fallbackReason);
      }
    }
  }

  // Offline fallback
  const offlineAns = generateOfflineAnswer(query, retrievalResult);
  offlineAns.cards = buildOfflineCards(retrievalResult.records);
  return {
    mode: 'offline',
    badge: BADGE_OFFLINE,
    fallback_reason: fallbackReason,
    query: retrievalResult.query,
    records_retrieved: retrievalResult.records.length,
    records: retrievalResult.records,
    answer: offlineAns,
    is_low_evidence: retrievalResult.is_low_evidence,
    is_out_of_corpus: retrievalResult.is_out_of_corpus,
    model_used: 'none (offline-retrieval)',
  };
}

/**
 * Serverless HTTP Request Handler (Vercel Node.js function)
 */
export default async function handler(req, res) {
  // Set CORS headers
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  if (req.method === 'OPTIONS') {
    res.statusCode = 200;
    res.end();
    return;
  }

  let query = '';
  if (req.method === 'POST') {
    let body = req.body;
    if (typeof body === 'string') {
      try {
        body = JSON.parse(body);
      } catch (e) {
        body = {};
      }
    }
    query = body?.query || '';
  } else if (req.method === 'GET') {
    const url = new URL(req.url, `http://${req.headers?.host || 'localhost'}`);
    query = url.searchParams.get('query') || '';
  }

  try {
    const responseData = await generateChatResponse(query);
    res.setHeader('Content-Type', 'application/json; charset=utf-8');
    res.statusCode = 200;
    res.end(JSON.stringify(responseData));
  } catch (err) {
    res.setHeader('Content-Type', 'application/json; charset=utf-8');
    res.statusCode = 500;
    res.end(JSON.stringify({
      error: 'Internal server error processing chat request.',
      details: err.message,
      badge: BADGE_OFFLINE,
    }));
  }
}

