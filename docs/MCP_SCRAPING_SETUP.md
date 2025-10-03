# MCP Server Setup for Web Scraping

## Current State vs Requirements

### Available MCP Servers
- ✅ Sequential MCP - Analysis and reasoning
- ✅ Serena MCP - Code navigation
- ✅ Context7 MCP - Documentation

### Missing Critical MCP Servers
- ❌ **Playwright MCP** - Browser automation (CRITICAL for Z-Library)
- ❌ HTML/DOM Parser MCP - Advanced HTML navigation
- ❌ HTTP Client MCP - Advanced request handling

## Why Playwright MCP is Critical

Z-Library's "Hydra mode" infrastructure presents challenges that basic HTTP scraping cannot handle:

1. **JavaScript-Rendered Pages**
   - Authentication flows may use JavaScript
   - Dynamic content loading
   - AJAX requests for book details

2. **CAPTCHA Challenges**
   - Z-Library may present CAPTCHAs during high traffic
   - Requires browser automation to handle
   - Current httpx/BeautifulSoup cannot solve CAPTCHAs

3. **Anti-Bot Detection**
   - Browser fingerprinting
   - Mouse movement tracking
   - JavaScript challenge-response tests

4. **Complex User Flows**
   - Multi-step authentication
   - Domain rotation with redirects
   - Session management with JavaScript

## Current Workaround (Limited)

The project currently uses Python-based scraping:

```python
# lib/python_bridge.py
import httpx
from bs4 import BeautifulSoup

# Basic HTML scraping - works for now but fragile
async def fetch_page(url):
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        return soup
```

**Limitations**:
- Cannot execute JavaScript
- Cannot handle CAPTCHAs
- May trigger bot detection
- Fails on dynamic content

## Recommended Setup: Playwright MCP

### Installation

```bash
# Install Playwright MCP server
npm install -g @modelcontextprotocol/server-playwright

# Install Playwright browsers
npx playwright install chromium
```

### Configuration (.mcp/config.json)

```json
{
  "servers": {
    "playwright": {
      "command": "npx",
      "args": ["@modelcontextprotocol/server-playwright"],
      "env": {
        "HEADLESS": "true",
        "TIMEOUT": "30000",
        "BROWSER": "chromium",
        "USER_AGENT": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
      }
    }
  }
}
```

### Integration with Z-Library Scraping

```typescript
// Enhanced scraping with Playwright MCP
class EnhancedZLibraryScraper {
  private playwright: PlaywrightMCP;

  async loginWithCaptchaHandling(email: string, password: string) {
    // Navigate to login
    await this.playwright.goto('https://singlelogin.me');

    // Fill credentials
    await this.playwright.fill('#email', email);
    await this.playwright.fill('#password', password);

    // Check for CAPTCHA
    const captcha = await this.playwright.isVisible('.g-recaptcha');
    if (captcha) {
      // Handle CAPTCHA (manual or service)
      await this.handleCaptcha();
    }

    // Submit form
    await this.playwright.click('#submit');

    // Wait for navigation
    await this.playwright.waitForNavigation();
  }

  async searchBooksWithJS(query: string) {
    // Handle JavaScript-rendered search
    await this.playwright.goto('/search');
    await this.playwright.fill('#search-input', query);

    // Wait for AJAX results
    await this.playwright.waitForSelector('.search-results');

    // Extract results after JS rendering
    return await this.playwright.evaluate(() => {
      return Array.from(document.querySelectorAll('.book-item')).map(el => ({
        title: el.querySelector('.title')?.textContent,
        author: el.querySelector('.author')?.textContent,
        downloadUrl: el.querySelector('.download-btn')?.href
      }));
    });
  }
}
```

## Alternative: Enhance Python Bridge

If Playwright MCP is not available, enhance the Python bridge:

### Option 1: Selenium Integration

```python
# lib/enhanced_scraping.py
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class EnhancedScraper:
    def __init__(self):
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        self.driver = webdriver.Chrome(options=options)

    def handle_dynamic_content(self, url):
        self.driver.get(url)
        # Wait for JS to render
        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located(("class", "book-content"))
        )
        return self.driver.page_source
```

### Option 2: Playwright Python

```python
# lib/playwright_bridge.py
from playwright.async_api import async_playwright

async def scrape_with_js(url):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(url)

        # Wait for dynamic content
        await page.wait_for_selector('.book-list')

        # Extract after JS execution
        content = await page.content()
        await browser.close()
        return content
```

## Testing Web Scraping Capabilities

### Test Suite for Scraping

```javascript
// __tests__/scraping-capabilities.test.js
describe('Web Scraping Capabilities', () => {
  test('Can handle static HTML', async () => {
    const result = await scrapeStaticPage('https://example.com/static');
    expect(result).toBeDefined();
  });

  test('Can handle JavaScript-rendered content', async () => {
    // This will FAIL without Playwright MCP
    const result = await scrapeDynamicPage('https://example.com/dynamic');
    expect(result).toBeDefined();
  });

  test('Can handle CAPTCHA challenges', async () => {
    // This will FAIL without browser automation
    const result = await scrapeWithCaptcha('https://example.com/captcha');
    expect(result).toBeDefined();
  });

  test('Can rotate domains on failure', async () => {
    const domains = ['domain1.com', 'domain2.com', 'domain3.com'];
    const result = await scrapeWithRotation(domains);
    expect(result).toBeDefined();
  });
});
```

## Risk Assessment

### Current Risk Level: 🟡 MEDIUM

**Working Now But At Risk**:
- Z-Library could add JavaScript requirements anytime
- CAPTCHA implementation would break current scraping
- Anti-bot measures could detect httpx patterns

### With Playwright MCP: 🟢 LOW

**Robust Against**:
- JavaScript requirements
- CAPTCHA challenges (with integration)
- Anti-bot detection
- Dynamic content changes

## Recommendations

### Immediate Actions
1. **Continue with current Python-based scraping** (working for now)
2. **Monitor for scraping failures** in production
3. **Plan Playwright MCP integration** for robustness

### When to Upgrade
Implement Playwright MCP when:
- Z-Library adds CAPTCHA challenges
- JavaScript becomes required for auth
- Current scraping success rate drops below 80%
- Users report consistent failures

### Integration Priority
1. **High Priority**: Login/authentication flows
2. **Medium Priority**: Search functionality
3. **Low Priority**: Static content pages

## Monitoring

Add metrics to track when browser automation becomes necessary:

```typescript
// Track scraping success rates
const metrics = {
  staticSuccess: 0,
  dynamicFailure: 0,
  captchaEncountered: 0,
  authFailures: 0
};

// Alert when thresholds exceeded
if (metrics.dynamicFailure > 10 || metrics.captchaEncountered > 0) {
  console.warn('Browser automation required - implement Playwright MCP');
}
```

---

**Last Updated**: 2025-01-30
**Status**: Python scraping working, Playwright MCP recommended for robustness
**Risk Level**: Medium (current) → Low (with Playwright)