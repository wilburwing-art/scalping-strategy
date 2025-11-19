# API Key Setup Guide

Complete instructions for obtaining all required API keys for the trading sentiment analysis features.

---

## 1. Twitter/X API Key

### Step-by-Step Instructions

1. **Go to Twitter Developer Portal**
   - Visit: https://developer.twitter.com/en/portal/dashboard
   - Sign in with your Twitter/X account

2. **Apply for Developer Account**
   - Click "Sign up for Free Account" (if you don't have one)
   - Select "Hobbyist" → "Exploring the API"
   - Fill out the required information:
     - What's your use case? → "Building a trading sentiment analysis tool"
     - Will you make Twitter content available to government? → No
   - Agree to Developer Agreement
   - Click "Submit"
   - Verify your email

3. **Create a New Project**
   - Once approved, click "Create Project"
   - Project name: `Trading Sentiment Analysis`
   - Use case: `Sentiment analysis and research`
   - Project description: `Analyzing market sentiment from social media for trading signals`

4. **Create an App**
   - App name: `ForexSentimentBot` (must be unique)
   - Click "Complete"

5. **Generate API Keys**
   - You'll see your keys immediately - SAVE THESE NOW:
     ```
     API Key (Consumer Key): abc123...
     API Secret (Consumer Secret): xyz789...
     Bearer Token: AAAA...
     ```
   - Copy and save to a secure location

6. **Configure App Permissions** (Optional for read-only)
   - Go to your app → Settings → User authentication settings
   - App permissions: Read (default is fine)

### Twitter API Limits (Free Tier)
- 1,500 tweets per month
- Read-only access
- No real-time streaming

### Add to Configuration
```ini
[twitter]
api_key = YOUR_API_KEY_HERE
api_secret = YOUR_API_SECRET_HERE
bearer_token = YOUR_BEARER_TOKEN_HERE
```

---

## 2. Reddit API Key

### Step-by-Step Instructions

1. **Log into Reddit**
   - Go to: https://www.reddit.com
   - Log in with your account (create one if needed)

2. **Go to App Preferences**
   - Visit: https://www.reddit.com/prefs/apps
   - Or: Reddit → Settings → Privacy & Security → Apps

3. **Create a New Application**
   - Scroll to bottom
   - Click "are you a developer? create an app..."

4. **Fill Out Application Form**
   ```
   Name: TradingSentimentBot
   App type: ○ script
   Description: Forex trading sentiment analysis
   About URL: (leave blank)
   Redirect URI: http://localhost:8080
   ```
   - Click "create app"

5. **Save Your Credentials**
   - After creation, you'll see:
     ```
     [Icon] TradingSentimentBot          [delete] [edit]
     personal use script
     CLIENT_ID_HERE                      <- This is under the app name
     secret: SECRET_KEY_HERE             <- This is labeled "secret"
     ```
   - Copy both values

### Reddit API Limits (Free)
- 60 requests per minute
- 600 requests per hour
- No additional cost

### Add to Configuration
```ini
[reddit]
client_id = YOUR_CLIENT_ID_HERE
client_secret = YOUR_CLIENT_SECRET_HERE
user_agent = TradingSentimentBot/1.0 by u/YOUR_REDDIT_USERNAME
```

---

## 3. Trading Economics API Key

### Step-by-Step Instructions

1. **Go to Trading Economics**
   - Visit: https://tradingeconomics.com/api

2. **Click "Sign Up"**
   - Or go directly to: https://tradingeconomics.com/api/register

3. **Create Free Account**
   - Fill out registration form:
     ```
     Email: your-email@example.com
     Password: (strong password)
     First Name: John
     Last Name: Doe
     Country: United States
     ```
   - Click "Sign Up"

4. **Verify Your Email**
   - Check your inbox for verification email
   - Click verification link

5. **Access API Dashboard**
   - Log in at: https://tradingeconomics.com/login
   - Go to: https://tradingeconomics.com/api/dashboard
   - Or click "API" → "Dashboard" in menu

6. **Copy Your API Key**
   - You'll see: `Your API Key: YOUR_API_KEY_HERE`
   - Click to copy

7. **Review Free Tier Limits**
   - Dashboard shows your usage
   - Free tier: 500 requests/day
   - Historical data: Limited to last 3 years

### Trading Economics Limits (Free Tier)
- 500 API calls per day
- Historical data: 3 years
- No credit card required

### Add to Configuration
```ini
[trading_economics]
api_key = YOUR_API_KEY_HERE
```

---

## Complete Configuration File Example

After obtaining all keys, update your `v20.conf` or create `apis.conf`:

```ini
# OANDA API (already configured)
[practice]
hostname = api-fxpractice.oanda.com
token = YOUR_PRACTICE_OANDA_TOKEN
account_id = YOUR_PRACTICE_ACCOUNT_ID

[live]
hostname = api-fxtrade.oanda.com
token = YOUR_LIVE_OANDA_TOKEN
account_id = YOUR_LIVE_ACCOUNT_ID

# OpenAI API (already configured)
[openai]
api_key = YOUR_OPENAI_API_KEY
model = gpt-4o
min_confidence = 0.6

# Twitter/X API
[twitter]
api_key = YOUR_TWITTER_API_KEY
api_secret = YOUR_TWITTER_API_SECRET
bearer_token = YOUR_TWITTER_BEARER_TOKEN

# Reddit API
[reddit]
client_id = YOUR_REDDIT_CLIENT_ID
client_secret = YOUR_REDDIT_CLIENT_SECRET
user_agent = TradingSentimentBot/1.0 by u/YOUR_USERNAME

# Trading Economics API
[trading_economics]
api_key = YOUR_TRADING_ECONOMICS_KEY
```

---

## Security Best Practices

1. **Never Commit API Keys to Git**
   ```bash
   # Add to .gitignore
   echo "v20.conf" >> .gitignore
   echo "apis.conf" >> .gitignore
   echo "*.conf" >> .gitignore
   ```

2. **Use Environment Variables (Alternative)**
   ```bash
   export TWITTER_API_KEY="..."
   export TWITTER_API_SECRET="..."
   export TWITTER_BEARER_TOKEN="..."
   export REDDIT_CLIENT_ID="..."
   export REDDIT_CLIENT_SECRET="..."
   export TRADING_ECONOMICS_KEY="..."
   ```

3. **Rotate Keys Regularly**
   - Twitter: Regenerate in Developer Portal
   - Reddit: Delete and recreate app
   - Trading Economics: Contact support

4. **Monitor Usage**
   - Twitter: https://developer.twitter.com/en/portal/dashboard
   - Reddit: Check rate limit headers in API responses
   - Trading Economics: https://tradingeconomics.com/api/dashboard

---

## Troubleshooting

### Twitter API
**Problem:** "Application is not authorized"
- Solution: Check app permissions, regenerate bearer token

**Problem:** Rate limit exceeded
- Solution: Free tier is 1,500 tweets/month, upgrade or wait for reset

### Reddit API
**Problem:** "401 Unauthorized"
- Solution: Check client_id and client_secret are correct, update user_agent

**Problem:** "429 Too Many Requests"
- Solution: Implement rate limiting (60 req/min), add delays between requests

### Trading Economics
**Problem:** "Invalid API key"
- Solution: Ensure key is copied correctly, check for extra spaces

**Problem:** "Daily limit exceeded"
- Solution: Free tier is 500 calls/day, optimize queries or upgrade

---

## Next Steps After Setup

1. **Test Each API**
   ```python
   # Test Twitter
   import requests
   headers = {"Authorization": f"Bearer {BEARER_TOKEN}"}
   response = requests.get("https://api.twitter.com/2/tweets/search/recent?query=EURUSD", headers=headers)
   print(response.json())

   # Test Reddit
   import praw
   reddit = praw.Reddit(client_id=CLIENT_ID, client_secret=CLIENT_SECRET, user_agent=USER_AGENT)
   print(reddit.user.me())

   # Test Trading Economics
   response = requests.get(f"https://api.tradingeconomics.com/calendar?c={API_KEY}")
   print(response.json())
   ```

2. **Implement Sentiment Analysis Features**
   - See `NEXT_STEPS.md` Phase 4 for implementation plan

3. **Monitor API Usage**
   - Set up logging for API calls
   - Implement rate limiting
   - Track monthly usage against quotas

---

## Cost Summary

| API | Free Tier | Paid Plans Start At | Recommended |
|-----|-----------|---------------------|-------------|
| Twitter/X | 1,500 tweets/month | $100/month (Basic) | Free tier sufficient for testing |
| Reddit | 60 req/min unlimited | N/A (free only) | Free tier sufficient |
| Trading Economics | 500 calls/day | $50/month | Free tier sufficient initially |
| **Total** | **$0/month** | **$150/month** | **Start with free tier** |

---

## Support Links

- **Twitter/X Developer**: https://developer.twitter.com/en/support
- **Reddit API**: https://www.reddit.com/r/redditdev
- **Trading Economics**: support@tradingeconomics.com
- **OANDA**: https://developer.oanda.com/rest-live-v20/introduction/
