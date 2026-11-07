/**
 * Groww SIP Retention Research Dashboard - Client Application Logic
 *
 * 1. Fetches and validates web/data/corpus.json against audited baseline metrics.
 * 2. Renders dynamic theme distribution bars, journey stages, opportunity ranking table, and limitations.
 * 3. Handles interactive chat queries against /api/chat with offline fallback.
 * 4. Manages mobile full-screen panel toggle.
 */

// Exact Badge Constants
const BADGE_LIVE = 'GROUNDED IN CORPUS - LIVE AI ANSWER';
const BADGE_OFFLINE = 'GROUNDED IN CORPUS - OFFLINE RETRIEVAL (no live AI)';

let corpusData = null;

// Initialize on DOM load
document.addEventListener('DOMContentLoaded', async () => {
  setupNavigation();
  setupMobileModal();
  setupChatHandlers();
  await loadAndRenderCorpus();
});

/**
 * Smooth navigation scrolling for sidebar items
 */
function setupNavigation() {
  const navItems = document.querySelectorAll('.nav-item');
  navItems.forEach((item) => {
    item.addEventListener('click', (e) => {
      e.preventDefault();
      navItems.forEach((n) => n.classList.remove('active'));
      item.classList.add('active');

      const targetId = item.getAttribute('href');
      if (targetId && targetId.startsWith('#')) {
        const el = document.querySelector(targetId);
        if (el) {
          el.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
      }
    });
  });
}

/**
 * Mobile Ask Panel Toggle
 */
function setupMobileModal() {
  const fab = document.getElementById('mobileFabAsk');
  const panel = document.getElementById('rightPanel');
  const closeBtn = document.getElementById('mobilePanelClose');

  if (fab && panel) {
    fab.addEventListener('click', () => {
      panel.classList.add('mobile-open');
    });
  }

  if (closeBtn && panel) {
    closeBtn.addEventListener('click', () => {
      panel.classList.remove('mobile-open');
    });
  }
}

/**
 * Load corpus.json and validate audited numbers.
 * Fails loudly if any metric deviates from the audited baseline.
 */
async function loadAndRenderCorpus() {
  const candidateUrls = ['data/corpus.json', '/data/corpus.json', 'web/data/corpus.json'];
  let loaded = false;

  for (const url of candidateUrls) {
    try {
      const res = await fetch(url);
      if (res.ok) {
        corpusData = await res.json();
        loaded = true;
        break;
      }
    } catch (e) {
      // Try next candidate path
    }
  }

  if (!loaded || !corpusData) {
    showFatalError('Failed to load web/data/corpus.json. Please ensure scripts/export_dashboard_data.py has run.');
    return;
  }

  // Audited Metric Validation
  const m = corpusData.summary_metrics;
  const records = corpusData.records || [];

  const validationErrors = [];
  if (records.length !== 203) validationErrors.push(`Total records mismatch: expected 203, got ${records.length}`);
  if (m.stated_pause !== 8) validationErrors.push(`Stated pause mismatch: expected 8, got ${m.stated_pause}`);
  if (m.stated_stop !== 8) validationErrors.push(`Stated stop mismatch: expected 8, got ${m.stated_stop}`);
  if (m.stated_continue !== 7) validationErrors.push(`Stated continue mismatch: expected 7, got ${m.stated_continue}`);
  if (m.stated_reduce !== 3) validationErrors.push(`Stated reduce mismatch: expected 3, got ${m.stated_reduce}`);
  if (m.n_labeled !== 26) validationErrors.push(`n_labeled mismatch: expected 26, got ${m.n_labeled}`);

  const counts = Object.values(m.theme_counts || {});
  const sortedCounts = counts.sort((a, b) => b - a);
  const expectedThemeCounts = [63, 34, 28, 23, 19, 12, 10, 7, 7];
  if (JSON.stringify(sortedCounts) !== JSON.stringify(expectedThemeCounts)) {
    validationErrors.push(`Theme counts mismatch: expected ${expectedThemeCounts}, got ${sortedCounts}`);
  }

  if (validationErrors.length > 0) {
    const errorMsg = 'AUDITED DATA INTEGRITY FAILURE:\n' + validationErrors.join('\n');
    console.error(errorMsg);
    showFatalError(errorMsg);
    return;
  }

  // Populate UI
  renderThemeBars(m.theme_counts);
  renderJourneyStages(corpusData.journey_stages);
  renderOpportunityTable(corpusData.opportunity_ranking);
  renderLimitations(corpusData.limitations);
}

/**
 * Display fatal integrity error banner in UI
 */
function showFatalError(message) {
  const banner = document.createElement('div');
  banner.style.cssText = 'position:fixed;top:0;left:0;right:0;background:#dc2626;color:#fff;padding:16px;z-index:9999;font-weight:bold;font-size:14px;text-align:center;box-shadow:0 4px 6px rgba(0,0,0,0.2);';
  banner.innerText = message;
  document.body.prepend(banner);
}

/**
 * Render the 9 Theme Distribution Bars proportional to max count (63).
 * Uncertain in grey (#94A3B8), actionable themes in Groww teal (#00B386).
 */
function renderThemeBars(themeCounts) {
  const container = document.getElementById('themeBarsList');
  if (!container || !themeCounts) return;

  const maxVal = 63; // Max theme count benchmark
  let html = '';

  for (const [theme, count] of Object.entries(themeCounts)) {
    const isUncertain = theme.toLowerCase().includes('uncertain');
    const widthPct = ((count / maxVal) * 100).toFixed(1);
    const dotClass = isUncertain ? 'theme-dot grey' : 'theme-dot';
    const fillClass = isUncertain ? 'theme-progress-fill grey' : 'theme-progress-fill';

    html += `
      <div class="theme-bar-row">
        <div class="theme-bar-header">
          <span class="theme-name"><span class="${dotClass}"></span>${escapeHtml(theme)}</span>
          <span class="theme-count">${count} records</span>
        </div>
        <div class="theme-progress-track">
          <div class="${fillClass}" style="width: ${widthPct}%;"></div>
        </div>
      </div>
    `;
  }

  container.innerHTML = html;
}

/**
 * Render Where Retention Breaks Journey Stages
 */
function renderJourneyStages(stages) {
  const container = document.getElementById('journeyStagesGrid');
  if (!container || !stages) return;

  let html = '';
  stages.forEach((stage) => {
    html += `
      <div class="stage-card">
        <div class="stage-card-top">
          <span class="stage-badge">${stage.stage_number}</span>
          <span class="stage-count-pill">${stage.record_count} records</span>
        </div>
        <div class="stage-title">${escapeHtml(stage.stage_name)}</div>
        <div class="stage-theme-name">${escapeHtml(stage.theme)}</div>
      </div>
    `;
  });

  container.innerHTML = html;
}

/**
 * Render Opportunity Ranker Table showing all columns and horizontal scrolling
 */
function renderOpportunityTable(opportunities) {
  const tbody = document.getElementById('opportunityTableBody');
  if (!tbody || !opportunities) return;

  let html = '';
  opportunities.forEach((item) => {
    const isMeasured = item.churn_link_display && item.churn_link_display.includes('measured');
    const churnBadgeClass = isMeasured ? 'pill-measured' : 'pill-placeholder';
    const confClass = item.is_low_sample ? 'confidence-tag low' : 'confidence-tag robust';
    const confLabel = item.is_low_sample ? 'Low sample' : 'Robust sample';

    html += `
      <tr>
        <td class="rank-col">#${item.rank}</td>
        <td class="theme-col">${escapeHtml(item.theme)}</td>
        <td>${item.freq_score.toFixed(1)}</td>
        <td><span class="${churnBadgeClass}">${escapeHtml(item.churn_link_display || `${item.churn_link} (placeholder)`)}</span></td>
        <td>${item.severity.toFixed(1)}</td>
        <td>${item.fixability.toFixed(1)}</td>
        <td class="score-col">${item.priority_score.toFixed(1)}</td>
        <td><span class="${confClass}">${confLabel}</span></td>
      </tr>
    `;
  });

  tbody.innerHTML = html;
}

/**
 * Render Methodology & Limitations cards
 */
function renderLimitations(limitations) {
  const container = document.getElementById('limitationsGrid');
  if (!container || !limitations) return;

  let html = '';
  limitations.forEach((item) => {
    html += `
      <div class="limitation-card">
        <div class="limitation-card-title">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>
          ${escapeHtml(item.title)}
        </div>
        <div class="limitation-card-summary">${escapeHtml(item.summary)}</div>
      </div>
    `;
  });

  container.innerHTML = html;
}

/**
 * Setup Chat query input and suggestion chips
 */
function setupChatHandlers() {
  const input = document.getElementById('chatQueryInput');
  const submitBtn = document.getElementById('btnAskSubmit');
  const chips = document.querySelectorAll('.question-chip');

  // Submit on button click
  if (submitBtn && input) {
    submitBtn.addEventListener('click', () => {
      executeChatQuery(input.value.trim());
    });
  }

  // Submit on Enter key
  if (input) {
    input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        executeChatQuery(input.value.trim());
      }
    });
  }

  // Chips click handler — strip any leading number prefix
  chips.forEach((chip) => {
    chip.addEventListener('click', () => {
      const q = chip.innerText.trim().replace(/^\s*\d+[.)]?\s*/, '');
      if (input) input.value = q;
      executeChatQuery(q);
    });
  });

  // Show more / Show fewer toggle
  const showMoreBtn = document.getElementById('showMoreToggle');
  if (showMoreBtn) {
    showMoreBtn.addEventListener('click', () => {
      const extras = document.querySelectorAll('.question-chip-extra');
      const showing = !extras[0]?.hidden;
      extras.forEach((el) => { el.hidden = showing; });
      showMoreBtn.textContent = showing ? 'Show more questions ▾' : 'Show fewer questions ▴';
    });
  }
}

/**
 * Execute chat inquiry against /api/chat or client-side fallback
 */
async function executeChatQuery(query) {
  if (!query) return;

  const resultContainer = document.getElementById('chatResponseContainer');
  const submitBtn = document.getElementById('btnAskSubmit');
  const input = document.getElementById('chatQueryInput');

  if (!resultContainer) return;

  // Show loading indicator
  submitBtn.disabled = true;
  resultContainer.innerHTML = `
    <div class="loading-indicator">
      <div class="spinner"></div>
      <span>Retrieving grounded feedback from 203 records...</span>
    </div>
  `;

  let responseData = null;

  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query }),
    });

    if (res.ok) {
      responseData = await res.json();
    }
  } catch (err) {
    console.warn('Network call to /api/chat failed, performing client-side retrieval:', err);
  }

  // Client-side offline fallback if server call fails
  if (!responseData) {
    responseData = executeClientSideFallback(query);
  }

  submitBtn.disabled = false;
  renderChatAnswer(responseData);
}

/**
 * Render retrieved synthesis and verbatim quotes in Ask panel
 */
function renderChatAnswer(data) {
  const container = document.getElementById('chatResponseContainer');
  if (!container) return;

  const isLive = data.mode === 'live';
  const badgeClass = isLive ? 'chat-badge-pill live' : 'chat-badge-pill offline';
  const badgeText = isLive ? BADGE_LIVE : BADGE_OFFLINE;

  const ans = data.answer || {};
  const whatSaid = ans.what_customers_said || 'No matching feedback found.';

  // Records retrieved
  const records = data.records || [];
  const retrievedCount = records.length;

  // Compute most common primary theme and its count
  const themeFreq = {};
  records.forEach(r => {
    const t = r.primary_theme || 'Unknown';
    themeFreq[t] = (themeFreq[t] || 0) + 1;
  });
  let topTheme = 'None';
  let topCount = 0;
  Object.entries(themeFreq).forEach(([t, c]) => {
    if (c > topCount) { topTheme = t; topCount = c; }
  });
  const totalCorpus = 203; // constant per spec
  const percent = ((topCount / totalCorpus) * 100).toFixed(1);

  // Build direct answer box (starts with "Among the N retrieved records,")
  let directSentence = whatSaid.replace(/\*\*/g, '').trim();
  const firstPeriod = directSentence.indexOf('.');
  if (firstPeriod !== -1) {
    directSentence = directSentence.slice(0, firstPeriod + 1).trim();
  }
  if (!directSentence.startsWith(`Among the ${retrievedCount} retrieved records,`)) {
    // If not already phrased that way, format cleanly
    directSentence = `Among the ${retrievedCount} retrieved records, customers reported feedback concerning ${topTheme.toLowerCase()}.`;
  }

  // Header tag chip + count line
  const headerMetaHtml = retrievedCount > 0 ? `
    <div class="chat-answer-meta-row">
      <span class="tag-chip">${escapeHtml(topTheme)}</span>
      <span class="record-count-line">${retrievedCount} records retrieved · ${topCount} of ${totalCorpus} in this theme (${percent}%)</span>
    </div>
  ` : '';

  // 2 or 3 point cards with short title, sentence, and record IDs
  let summaryCardsHtml = '';
  const cards = ans.cards || [];
  if (cards.length > 0) {
    summaryCardsHtml = `
      <div class="summary-cards-container">
        ${cards.slice(0, 3).map(c => `
          <div class="summary-card">
            <div class="summary-card-title">${escapeHtml(c.title)}</div>
            <div class="summary-card-sentence">${escapeHtml(c.sentence)}</div>
            <div class="summary-card-ids">${(c.record_ids || []).map(id => `<span class="id-pill">${escapeHtml(id)}</span>`).join(' ')}</div>
          </div>
        `).join('')}
      </div>
    `;
  }

  // Section "QUOTES FROM THE FEEDBACK" with verbatim quotes, source label, ID, excerpt if truncated
  let quotesHtml = '';
  if (records.length > 0) {
    quotesHtml = `
      <div class="response-section-title" style="margin-top: 16px;">QUOTES FROM THE FEEDBACK</div>
      <div class="quotes-feedback-list">
        ${records.map(r => {
          const isTruncated = r.text.length > 180;
          const displayText = isTruncated ? `${r.text.slice(0, 180)}...` : r.text;
          const excerptBadge = isTruncated ? `<span class="excerpt-tag">Verbatim excerpt</span>` : `<span class="excerpt-tag">Verbatim quote</span>`;
          return `
            <div class="quote-feedback-item">
              <div class="quote-item-header">
                <span class="quote-item-id">${escapeHtml(r.feedback_id)}</span>
                <span class="quote-item-source">${escapeHtml(r.source_display || r.source)}</span>
                ${excerptBadge}
              </div>
              <div class="quote-item-text">"${escapeHtml(displayText)}"</div>
            </div>
          `;
        }).join('')}
      </div>
    `;
  }

  // Footer line with mode badge, optional fallback reason, and caveat
  const fallbackReasonHtml = (!isLive && data.fallback_reason) ? `
    <span class="chat-fallback-reason">${escapeHtml(data.fallback_reason)}</span>
  ` : '';

  const footerHtml = `
    <div class="chat-answer-footer">
      <span class="${badgeClass}">${badgeText}</span>
      ${fallbackReasonHtml}
      <span class="answer-caveat-text">Theme labels come from a rule-based classifier validated on 20 records.</span>
    </div>
  `;

  container.innerHTML = `
    <div class="chat-response-card">
      ${headerMetaHtml}
      <h3 class="user-question-heading">${escapeHtml(data.query)}</h3>
      <div class="direct-answer-box">
        <span class="direct-answer-label">DIRECT ANSWER</span>
        <p class="direct-answer-text">${escapeHtml(directSentence)}</p>
      </div>
      ${summaryCardsHtml}
      ${quotesHtml}
      ${footerHtml}
    </div>
  `;
}



/**
 * Client-side keyword retrieval fallback if hosted statically
 */
function executeClientSideFallback(query) {
  const records = corpusData?.records || [];
  const qLower = query.toLowerCase();

  // Out of corpus check
  if (/\b(f&o|fno|futures|options?|derivatives?|intraday|crypto|bitcoin|ethereum)\b/i.test(qLower)) {
    return {
      mode: 'offline',
      badge: BADGE_OFFLINE,
      query,
      records_retrieved: 0,
      fallback_reason: 'out of corpus query',
      records: [],
      answer: {
        what_customers_said: `The query "${query}" asks about derivatives or assets outside the mutual fund SIP discovery corpus. The engine contains 203 mutual fund and platform records and zero F&O or crypto data.`,
        interpretation: 'No mutual fund SIP conclusions can be drawn for out-of-scope assets.',
      },
    };
  }

  const queryTerms = qLower.split(/\s+/).filter((w) => w.length > 2);
  const scored = [];

  for (const r of records) {
    let score = 0;
    const textLower = r.text.toLowerCase();
    for (const term of queryTerms) {
      if (textLower.includes(term)) score += 1;
      if (r.primary_theme.toLowerCase().includes(term)) score += 2;
    }
    if (score > 0) {
      scored.push({ ...r, relevance_score: score });
    }
  }

  scored.sort((a, b) => b.relevance_score - a.relevance_score);
  const top = scored.slice(0, 5);

  if (top.length === 0) {
    return {
      mode: 'offline',
      badge: BADGE_OFFLINE,
      query,
      records_retrieved: 0,
      fallback_reason: 'out of corpus query',
      records: [],
      answer: {
        what_customers_said: `Insufficient evidence: No mutual fund feedback records closely match "${query}".`,
        interpretation: 'The corpus does not contain enough data to draw reliable conclusions on this topic.',
      },
    };
  }

  const quotesText = top.map((r, i) => `${i + 1}. [${r.feedback_id}] (${r.source_display}): "${r.text.slice(0, 180)}..."`).join('\n\n');

  return {
    mode: 'offline',
    badge: BADGE_OFFLINE,
    fallback_reason: 'no key set (client-side fallback)',
    query,
    records_retrieved: top.length,
    records: top,
    answer: {
      what_customers_said: `Based on ${top.length} retrieved feedback records matching "${query}":\n\n${quotesText}`,
      interpretation: 'Customer feedback indicates specific operational or informational friction points. These mentions reflect subjective user experiences and should not be treated as proof of single-variable churn causation. No investment advice provided.',
    },
  };
}

function escapeHtml(text) {
  if (!text) return '';
  return String(text)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

