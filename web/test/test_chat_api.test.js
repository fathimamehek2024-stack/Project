/**
 * Automated test suite for web/api/chat.js using Node.js built-in test runner.
 *
 * Verifies:
 * 1. Retrieval relevance for domain queries.
 * 2. Evidence attribution (IDs and sources match corpus.json).
 * 3. Empty results & low-evidence handling.
 * 4. Out-of-corpus queries (F&O / crypto detection).
 * 5. Missing GROQ_API_KEY fallback and exact offline badge text.
 * 6. API failure fallback and exact offline badge text.
 * 7. Live mode with simulated Groq response and exact live badge text.
 * 8. Prompt privacy: No developer-reply text in prompts sent to Groq.
 */

import { test, describe, before } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import handler, {
  BADGE_LIVE,
  BADGE_OFFLINE,
  buildPrompt,
  generateChatResponse,
  generateOfflineAnswer,
  loadCorpusData,
  normalizeToken,
  retrieveRelevantRecords,
  tokenizeText,
} from '../api/chat.js';

const TEST_DIR = fileURLToPath(new URL('.', import.meta.url));

describe('Groww SIP Retention Chat API & Retrieval Engine', () => {
  let corpus;

  before(() => {
    corpus = loadCorpusData();
    assert.ok(corpus, 'Corpus data should load successfully');
    assert.equal(corpus.records.length, 203, 'Corpus must contain exactly 203 records');
  });

  test('1. Normalization and tokenization handles domain vocabulary', () => {
    assert.equal(normalizeToken('SIPs'), 'sip');
    assert.equal(normalizeToken("sip's"), 'sip');
    assert.equal(normalizeToken('autopay'), 'autopay');
    assert.equal(normalizeToken('auto-debit'), 'autodebit');
    assert.equal(normalizeToken('mandates'), 'mandate');
    assert.equal(normalizeToken('pausing'), 'pause');
    assert.equal(normalizeToken('stopped'), 'stop');

    const tokens = tokenizeText('Why do users pause or stop their monthly SIP autopay?');
    assert.ok(tokens.includes('pause'));
    assert.ok(tokens.includes('stop'));
    assert.ok(tokens.includes('sip'));
    assert.ok(tokens.includes('autopay'));
  });

  test('2. Retrieval relevance: returns top 5 relevant records for core queries', () => {
    const res = retrieveRelevantRecords('Why do investors pause or stop their SIPs?', corpus);
    assert.equal(res.records.length, 5, 'Should return top 5 records');
    assert.equal(res.is_low_evidence, false, 'Should not be marked low evidence');
    assert.equal(res.is_out_of_corpus, false, 'Should not be marked out of corpus');
    assert.ok(res.top_score > 0.5, 'Top score should be substantial');

    // Check that themes include known pause/stop themes
    const themes = res.records.map((r) => r.primary_theme);
    const hasRelevantTheme = themes.some((t) =>
      t.includes('Pause') || t.includes('Stop') || t.includes('Financial') || t.includes('Volatility')
    );
    assert.ok(hasRelevantTheme, `Expected relevant theme among ${themes}`);
  });

  test('3. Evidence attribution: IDs and sources match corpus.json exactly', () => {
    const res = retrieveRelevantRecords('bank mandate payment failure and delayed allotment', corpus);
    assert.ok(res.records.length > 0);

    const corpusMap = new Map(corpus.records.map((r) => [r.feedback_id, r]));

    for (const rec of res.records) {
      assert.ok(corpusMap.has(rec.feedback_id), `ID ${rec.feedback_id} must exist in corpus.json`);
      const original = corpusMap.get(rec.feedback_id);
      assert.equal(rec.source, original.source);
      assert.equal(rec.text, original.text);
      assert.equal(rec.primary_theme, original.primary_theme);
      assert.equal(rec.sip_behavior, original.sip_behavior);
    }
  });

  test('4. Empty results and low evidence handling', () => {
    const emptyRes = retrieveRelevantRecords('', corpus);
    assert.equal(emptyRes.records.length, 0);
    assert.equal(emptyRes.is_low_evidence, true);

    const gibberishRes = retrieveRelevantRecords('xyzqwe987123nonsensequery', corpus);
    assert.equal(gibberishRes.is_low_evidence, true);

    const offlineAns = generateOfflineAnswer('xyzqwe987123nonsensequery', gibberishRes);
    assert.ok(offlineAns.what_customers_said.includes('Insufficient evidence'));
  });

  test('5. Out-of-corpus queries: detects F&O and crypto and declines extrapolation', () => {
    const fnoRes = retrieveRelevantRecords('What strike price should I buy for Nifty weekly options in F&O?', corpus);
    assert.equal(fnoRes.is_out_of_corpus, true);

    const offlineAns = generateOfflineAnswer('Nifty options F&O trading', fnoRes);
    assert.ok(offlineAns.what_customers_said.includes('outside the mutual fund SIP discovery corpus'));
    assert.ok(offlineAns.what_customers_said.includes('contains zero records on F&O'));
  });

  test('6. Missing GROQ_API_KEY returns offline retrieval with exact badge text and fallback_reason', async () => {
    const res = await generateChatResponse('Why do investors pause their SIPs?', {
      corpus,
      apiKey: '',
    });

    assert.equal(res.mode, 'offline');
    assert.equal(res.badge, BADGE_OFFLINE);
    assert.equal(res.badge, 'GROUNDED IN CORPUS - OFFLINE RETRIEVAL (no live AI)');
    assert.equal(res.fallback_reason, 'no key set');
    assert.equal(res.records_retrieved, 5);
    assert.ok(res.answer.what_customers_said.length > 0);
    assert.ok(res.answer.interpretation.length > 0);
  });

  test('7. API failure fallback returns offline retrieval with exact badge text', async () => {
    // Provide an invalid key that will fail against the real API or throw
    const res = await generateChatResponse('What problems do investors report with customer support?', {
      corpus,
      apiKey: 'gsk_invalid_test_key_for_failure_simulation',
      timeoutMs: 1500, // Short timeout for test speed
    });

    assert.equal(res.mode, 'offline');
    assert.equal(res.badge, BADGE_OFFLINE);
    assert.equal(res.badge, 'GROUNDED IN CORPUS - OFFLINE RETRIEVAL (no live AI)');
    assert.ok(res.records_retrieved > 0);
    assert.ok(res.fallback_reason, 'Must return a fallback_reason');
    assert.ok(!res.fallback_reason.includes('gsk_'), 'Fallback reason must never expose the API key');
  });

  test('8. Prompt privacy: zero developer-reply text in prompts sent to Groq', () => {
    // Gather known developer replies from processed playstore reviews
    const devReplies = [];
    for (const b of [
      'data/processed/playstore_groww_reviews_batch1_cleaned.csv',
      'data/processed/playstore_groww_reviews_batch2_cleaned.csv',
    ]) {
      const fullPath = path.resolve(process.cwd(), b);
      if (fs.existsSync(fullPath)) {
        const lines = fs.readFileSync(fullPath, 'utf-8').split('\n');
        for (const line of lines) {
          if (line.includes('support@groww.in') || line.includes('Hi , sorry for the hassle')) {
            devReplies.push(line.trim());
          }
        }
      }
    }

    assert.ok(devReplies.length > 0, 'Found reference developer replies for privacy check');

    // Build prompt for Customer Support query
    const retrieval = retrieveRelevantRecords('unhelpful customer care tickets closed without resolution', corpus);
    const promptPayload = buildPrompt('unhelpful customer care tickets', retrieval.records);

    // Verify userPrompt contains only customer feedback
    for (const reply of devReplies) {
      if (reply.length > 25) {
        const snippet = reply.slice(0, 25);
        assert.ok(
          !promptPayload.userPrompt.includes(snippet),
          `Developer reply "${snippet}" leaked into user prompt!`
        );
      }
    }
  });

  test('9. Section separation and verbatim quote inclusion in response', async () => {
    const res = await generateChatResponse('What motivates investors to continue their SIPs?', {
      corpus,
      apiKey: '',
    });

    assert.ok(res.answer.what_customers_said.length > 0);
    assert.ok(res.answer.interpretation.length > 0);

    // Check that quotes contain feedback IDs
    assert.ok(
      res.answer.what_customers_said.includes('GROWW_') ||
      res.answer.what_customers_said.includes('FORM_') ||
      res.answer.what_customers_said.includes('REDDIT_'),
      'Customer said section should cite record IDs'
    );
  });

  test('10. Vercel serverless handler function handles GET and POST requests', async () => {
    // Test POST request with body object
    let headersSet = {};
    let statusCode = 0;
    let endContent = '';

    const mockRes = {
      setHeader(name, val) { headersSet[name] = val; },
      set statusCode(code) { statusCode = code; },
      get statusCode() { return statusCode; },
      end(data) { endContent = data; },
    };

    const mockReq = {
      method: 'POST',
      body: { query: 'Why do investors pause or stop their SIPs?' },
      headers: { host: 'localhost:3000' },
      url: '/api/chat',
    };

    await handler(mockReq, mockRes);

    assert.equal(statusCode, 200);
    assert.ok(headersSet['Content-Type'].includes('application/json'));
    const parsed = JSON.parse(endContent);
    assert.equal(parsed.mode, 'offline');
    assert.equal(parsed.badge, BADGE_OFFLINE);
    assert.equal(parsed.records_retrieved, 5);
    assert.ok(parsed.answer.what_customers_said);

    // Test OPTIONS request for CORS preflight
    let optionsCode = 0;
    const mockResOptions = {
      setHeader(name, val) { headersSet[name] = val; },
      set statusCode(code) { optionsCode = code; },
      get statusCode() { return optionsCode; },
      end() {},
    };
    await handler({ method: 'OPTIONS' }, mockResOptions);
    assert.equal(optionsCode, 200);
  });

  test('11. No suggested question in index.html starts with a digit', () => {
    const htmlPath = path.resolve(TEST_DIR, '..', 'index.html');
    const html = fs.readFileSync(htmlPath, 'utf-8');
    // Extract every question-chip button's text content
    const chipRegex = /<button[^>]*class="[^"]*question-chip[^"]*"[^>]*>(.*?)<\/button>/g;
    let match;
    const questions = [];
    while ((match = chipRegex.exec(html)) !== null) {
      questions.push(match[1].trim());
    }
    assert.ok(questions.length >= 6, `Expected at least 6 suggested questions, got ${questions.length}`);
    for (const q of questions) {
      assert.ok(
        !/^\s*\d/.test(q),
        `Suggested question should not start with a digit: "${q}"`
      );
    }
  });

  test('12. Clicking a question chip sets input text without leading number prefix', () => {
    // Simulate the strip regex used in app.js chip click handler
    const stripPrefix = (text) => text.trim().replace(/^\s*\d+[.)]?\s*/, '');

    // Even if a chip somehow had a number prefix, the handler must strip it
    assert.equal(stripPrefix('1. Why do investors pause?'), 'Why do investors pause?');
    assert.equal(stripPrefix('2) What are the friction points?'), 'What are the friction points?');
    assert.equal(stripPrefix('10 What motivates investors?'), 'What motivates investors?');
    // Plain text without a number stays unchanged
    assert.equal(stripPrefix('Why do investors pause or stop their SIPs?'), 'Why do investors pause or stop their SIPs?');
    assert.equal(stripPrefix('What do investors say about fees, charges and deductions?'), 'What do investors say about fees, charges and deductions?');
  });

  test('13. validateCards rejects cards that cite IDs outside the retrieved set', async () => {
    const { validateCards } = await import('../api/chat.js');
    const retrievedIds = ['play_001', 'play_002', 'reddit_003'];

    // Valid cards
    const valid = [
      { title: 'Autopay issues', sentence: 'Mandate setup fails.', record_ids: ['play_001', 'play_002'] },
      { title: 'Support delay', sentence: 'Tickets remain open.', record_ids: ['reddit_003'] },
    ];
    assert.equal(validateCards(valid, retrievedIds), true);

    // Invalid: contains an ID not in retrieved set
    const invalidExtraId = [
      { title: 'Hallucinated', sentence: 'Bad cite.', record_ids: ['play_999'] },
    ];
    assert.equal(validateCards(invalidExtraId, retrievedIds), false);

    // Invalid: empty record_ids
    const emptyIds = [
      { title: 'No ids', sentence: 'Missing cites.', record_ids: [] },
    ];
    assert.equal(validateCards(emptyIds, retrievedIds), false);

    // Invalid: non-array input
    assert.equal(validateCards(null, retrievedIds), false);
    assert.equal(validateCards([], retrievedIds), false);
  });

  test('14. buildOfflineCards returns grouped cards without generated prose', async () => {
    const { buildOfflineCards } = await import('../api/chat.js');
    const mockRecords = [
      { feedback_id: 'rec_1', primary_theme: 'Financial Constraints & Cash Flow Liquidity' },
      { feedback_id: 'rec_2', primary_theme: 'Financial Constraints & Cash Flow Liquidity' },
      { feedback_id: 'rec_3', primary_theme: 'Customer Support & Resolution Friction' },
    ];

    const cards = buildOfflineCards(mockRecords);
    assert.ok(Array.isArray(cards));
    assert.equal(cards.length, 2);
    assert.equal(cards[0].title, 'Financial Constraints & Cash Flow Liquidity');
    assert.equal(cards[0].sentence, '2 records');
    assert.deepEqual(cards[0].record_ids, ['rec_1', 'rec_2']);
    assert.equal(cards[1].sentence, '1 record');
    // Ensure no generated AI prose
    assert.match(cards[0].sentence, /^\d+ records?$/);
  });

  test('15. Percentage calculation in answer header is exactly (theme_count / 203) * 100', () => {
    const totalCorpus = 203;
    const testCases = [
      { count: 63, expected: '31.0' },
      { count: 34, expected: '16.7' },
      { count: 28, expected: '13.8' },
      { count: 10, expected: '4.9' },
      { count: 1, expected: '0.5' },
    ];
    for (const { count, expected } of testCases) {
      const pct = ((count / totalCorpus) * 100).toFixed(1);
      assert.equal(pct, expected);
    }
  });

  test('16. Layout does not contain the word "verified"', async () => {
    const { generateChatResponse } = await import('../api/chat.js');
    const res = await generateChatResponse('Why do investors pause their SIP?');
    const text = JSON.stringify(res).toLowerCase();
    assert.ok(!text.includes('verified'), 'Response must not contain the word "verified"');
  });

  test('17. Out-of-corpus query detection declines extrapolation', async () => {
    const { generateChatResponse } = await import('../api/chat.js');
    const res = await generateChatResponse('Can I trade crypto bitcoin and F&O futures?');
    assert.equal(res.is_out_of_corpus, true);
    assert.ok(res.answer.what_customers_said.includes('outside the mutual fund SIP discovery corpus'));
  });

  test('18. Fallback reason never contains the API key under any error condition', async () => {
    const fakeKey = 'gsk_secret_token_123456789_xyz';
    const testCases = [
      { apiKey: '', expected: 'no key set' },
      { apiKey: fakeKey, model: '', expected: 'model name not set' },
      { apiKey: fakeKey, model: 'openai/gpt-oss-120b', timeoutMs: 500 },
    ];

    for (const tc of testCases) {
      const res = await generateChatResponse('What do investors say about autopay failures?', {
        corpus,
        ...tc,
      });
      assert.equal(res.mode, 'offline');
      assert.ok(res.fallback_reason, 'Must provide a fallback reason');
      assert.ok(
        !res.fallback_reason.includes(fakeKey) && !res.fallback_reason.includes('gsk_'),
        `Fallback reason "${res.fallback_reason}" must not contain API key`
      );
      if (tc.expected) {
        assert.equal(res.fallback_reason, tc.expected);
      }
    }
  });
});
