# API Configuration Status

Last Updated: 2025-11-15

## ✅ Working APIs

### 1. OANDA (Trading Platform)
**Status:** ✅ Configured & Working
**Environment:** Practice Account
**Account:** 101-001-30773717-001
**Purpose:** Real-time forex price data & trade execution

---

### 2. OpenAI (AI Agents)
**Status:** ⚠️ Needs Configuration
**Purpose:** Multi-agent trading intelligence system
**Required:** Set `OPENAI_API_KEY` environment variable or update v20.conf
**Models:** gpt-4o (recommended), gpt-4o-mini (lower cost)

---

### 3. Twitter/X API
**Status:** ✅ Configured & Working
**Access Level:** Free Tier
**Limits:**
- Recent search: 3 requests per 15 minutes
- Monthly cap: 1,500 tweets
**Purpose:** Social sentiment analysis for forex pairs

**Test Results:**
```bash
✓ Successfully retrieved 10 forex-related tweets
✓ User lookup working
✓ Rate limits confirmed
```

**⚠️ SECURITY WARNING:**
API keys were exposed in conversation. Regenerate at:
https://developer.twitter.com/en/portal/projects-and-apps

---

### 4. Alpha Vantage (News & Economic Data)
**Status:** ✅ Configured & Working
**Access Level:** Free Tier
**API Key:** 4QXEZDX1W9BNFGVK
**Limits:**
- 500 API calls per day
- 25 calls per minute

**Available Endpoints:**
- ✅ News Sentiment (50 articles retrieved)
- ✅ Forex Exchange Rates (EURUSD: 1.16250)
- ✅ Economic Calendar Events
- ✅ Market News by Topic

**Test Results:**
```bash
✓ PASS - News Sentiment
✓ PASS - Forex Data
✓ PASS - Economic Calendar
```

---

## ⏳ Pending APIs

### 5. Reddit API
**Status:** ⏳ Waiting for Support Response
**Issue:** Hit application creation limit
**Action:** Support ticket submitted
**Alternative:** Can use existing app if available, or skip (Twitter is sufficient)

---

## 📊 API Coverage Summary

| Data Source | Provider | Status | Free Tier | Purpose |
|-------------|----------|--------|-----------|---------|
| Price Data | OANDA | ✅ Working | Practice: Yes | Real-time forex quotes |
| Trade Execution | OANDA | ✅ Working | Practice: Yes | Order placement |
| AI Analysis | OpenAI | ⚠️ Setup Needed | No ($0.002/1K tokens) | Trading signals |
| Social Sentiment | Twitter | ✅ Working | 1,500 tweets/mo | Retail trader sentiment |
| News Sentiment | Alpha Vantage | ✅ Working | 500 calls/day | Market-moving news |
| Economic Calendar | Alpha Vantage | ✅ Working | 500 calls/day | Major events (NFP, Fed) |
| Forex Rates | Alpha Vantage | ✅ Working | 500 calls/day | Backup price source |
| Reddit Sentiment | Reddit | ⏳ Pending | 60 req/min | Optional (can skip) |

---

## 🔐 Security Checklist

- ✅ v20.conf added to .gitignore
- ✅ API keys stored in config file (not hardcoded)
- ⚠️ **TODO:** Regenerate Twitter API keys (exposed in conversation)
- ⚠️ **TODO:** Set OpenAI API key environment variable
- ✅ Alpha Vantage key configured

---

## 📈 Cost Analysis

### Monthly Costs (Free Tier)
- OANDA Practice: **$0**
- Twitter Free Tier: **$0** (limited to 1,500 tweets/month)
- Alpha Vantage Free: **$0** (limited to 500 calls/day)
- Reddit: **$0** (when approved)

**Total Free Tier Cost: $0/month**

### Optional Upgrades
- Twitter Basic: **$100/month** (10,000 tweets/month, better search)
- OpenAI GPT-4o: **~$5-20/month** (depends on usage)
- Alpha Vantage Premium: **$49/month** (unlimited calls)

**Recommended Starting Budget: $5-20/month** (just OpenAI)

---

## 🚀 Next Steps

1. **Set OpenAI API Key** (Required for AI agents)
   ```bash
   export OPENAI_API_KEY="sk-..."
   # OR add to v20.conf [openai] section
   ```

2. **Regenerate Twitter Keys** (Security best practice)
   - Go to: https://developer.twitter.com/en/portal/projects-and-apps
   - Regenerate all keys
   - Update v20.conf

3. **Test Full Integration**
   ```bash
   # Test all APIs
   uv run test_twitter_api.py
   uv run test_alpha_vantage.py

   # Run strategy with AI agents
   export OPENAI_API_KEY="sk-..."
   uv run enhanced_scalping_strategy.py
   ```

4. **Optional: Wait for Reddit** (or skip - Twitter is sufficient)

---

## 📝 Configuration File Location

**File:** `/Users/wilburpyn/repos/scalping-strategy/v20.conf`

**Sections:**
- `[practice]` - OANDA practice account
- `[live]` - OANDA live account (not configured)
- `[openai]` - AI agent configuration
- `[twitter]` - Social sentiment
- `[reddit]` - Social sentiment (pending)
- `[alpha_vantage]` - News & economic data
- `[sentiment]` - Sentiment analysis settings
- `[alerts]` - Email/SMS alerts (not configured)
- `[monitoring]` - System health monitoring

---

## 🧪 Test Scripts

**Available Test Files:**
1. `test_twitter_api.py` - Verify Twitter connection
2. `test_alpha_vantage.py` - Verify Alpha Vantage connection

**Run tests:**
```bash
cd /Users/wilburpyn/repos/scalping-strategy
uv run test_twitter_api.py
uv run test_alpha_vantage.py
```

---

## 📚 API Documentation

- **OANDA:** https://developer.oanda.com/rest-live-v20/introduction/
- **Twitter:** https://developer.twitter.com/en/docs/twitter-api
- **Alpha Vantage:** https://www.alphavantage.co/documentation/
- **OpenAI:** https://platform.openai.com/docs/api-reference
- **Reddit:** https://www.reddit.com/dev/api (when approved)

---

## ✅ Ready to Trade

**Minimum Required APIs for Basic Trading:**
- ✅ OANDA (price data + execution)
- ⚠️ OpenAI (for AI agents - optional but recommended)

**Enhanced Trading with Full Features:**
- ✅ OANDA (price data + execution)
- ⚠️ OpenAI (AI agent intelligence)
- ✅ Twitter (social sentiment)
- ✅ Alpha Vantage (news sentiment + economic calendar)
- ⏳ Reddit (optional - adds more sentiment data)

**Current Status: 75% Ready** (3/4 required APIs working)

Set your OpenAI API key to reach 100% readiness!
