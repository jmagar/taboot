# Multilingual Website Crawling Best Practices

## Executive Summary

This document outlines industry best practices for controlling language/locale when crawling multilingual websites. It covers HTTP header configuration, URL patterns, cookie handling, and strategies to prevent unwanted auto-redirects to localized content.

## Table of Contents

1. [HTTP Accept-Language Header](#http-accept-language-header)
2. [URL-Based Locale Patterns](#url-based-locale-patterns)
3. [Cookie-Based Language Selection](#cookie-based-language-selection)
4. [Query Parameter Approaches](#query-parameter-approaches)
5. [Preventing Auto-Redirects](#preventing-auto-redirects)
6. [Implementation Patterns](#implementation-patterns)
7. [Firecrawl-Specific Configuration](#firecrawl-specific-configuration)
8. [Playwright Browser Emulation](#playwright-browser-emulation)
9. [Recommendations for Taboot](#recommendations-for-taboot)

---

## HTTP Accept-Language Header

### Specification (RFC 9110)

The `Accept-Language` HTTP header allows browsers/crawlers to indicate preferred languages for content negotiation.

**Syntax:**

```http
Accept-Language: <language>
Accept-Language: *

# Multiple languages with quality values (q-factor weighting)
Accept-Language: fr-CH, fr;q=0.9, en;q=0.8, de;q=0.7, *;q=0.5
```

**Components:**

- **Language tag**: 2-3 letter base language (e.g., `en`, `de`, `zh`) optionally followed by subtags:
  - Region variant: `en-US`, `en-GB`, `fr-CA`, `pt-BR`
  - Script type: `sr-Latn` (Serbian in Latin script), `zh-Hans` (Simplified Chinese)
  - Orthography: `de-DE-1996` (German 1996 spelling reform)

- **Quality value (q-factor)**: Range 0.0-1.0 (default 1.0) indicating preference strength
  - Higher values = stronger preference
  - Allows fallback chains: primary → secondary → tertiary

- **Wildcard (`*`)**: Matches any language not explicitly listed

**Examples:**

```http
# Prefer English only
Accept-Language: en

# Prefer Danish, fallback to British English, then any English
Accept-Language: da, en-GB;q=0.8, en;q=0.7

# Prefer German, fallback to English
Accept-Language: de-DE, de;q=0.9, en;q=0.5

# Prefer US English, but accept any language if unavailable
Accept-Language: en-US, *;q=0.1
```

### Best Practices

1. **Always send Accept-Language** - Even for English-only crawling, explicitly set `Accept-Language: en-US, en;q=0.9`
2. **Use quality values for fallback chains** - Provide graceful degradation (e.g., `en-US, en;q=0.9, *;q=0.1`)
3. **Region-specific when needed** - Use `en-US` vs `en-GB` only if content differs by region
4. **Avoid wildcards alone** - `Accept-Language: *` means "accept anything" (unpredictable results)

### Common Pitfalls

- **Empty header**: Some sites default to browser/IP geolocation if missing
- **Too many languages**: Listing 10+ languages can confuse content negotiation
- **Case sensitivity**: Language tags are case-insensitive (`en-US` == `en-us`), but lowercase is convention

---

## URL-Based Locale Patterns

Many multilingual sites encode language/region in URL structure.

### Pattern Types

#### 1. Subdomain-based

```
https://en.example.com/
https://de.example.com/
https://fr.example.com/
```

**Pros:** Clean separation, easy CDN configuration
**Cons:** DNS overhead, SSL cert management per subdomain

#### 2. Path-based (most common)

```
https://example.com/en/page
https://example.com/de/page
https://example.com/fr/page
```

**Pros:** Single domain, simple routing, SEO-friendly
**Cons:** Requires server-side routing logic

#### 3. TLD-based (country-specific)

```
https://example.com/ (US)
https://example.co.uk/ (UK)
https://example.de/ (Germany)
https://example.fr/ (France)
```

**Pros:** Strong regional association, best for country-specific content
**Cons:** Expensive (multiple domains), complex operations

#### 4. Mixed patterns

```
https://example.com/en-US/page (language + region)
https://example.com/markets/europe/de/page (hierarchical)
```

### Crawling Strategy for URL Patterns

**Explicit URL targeting:**

```python
# Force English path-based URLs
target_url = "https://example.com/en/docs"

# For subdomain patterns
target_url = "https://en.example.com/docs"
```

**Dynamic locale injection:**

```python
def localize_url(base_url: str, locale: str = "en") -> str:
    """Inject locale into URL if not present."""
    parsed = urlparse(base_url)
    path = parsed.path.strip("/")

    # Check if locale already in path
    if not path.startswith(f"{locale}/"):
        path = f"{locale}/{path}"

    return parsed._replace(path=f"/{path}").geturl()

# Usage
url = localize_url("https://example.com/docs", "en")
# → https://example.com/en/docs
```

---

## Cookie-Based Language Selection

Some sites store language preference in cookies (e.g., `lang=en`, `locale=en-US`).

### Common Cookie Names

```
lang=en
language=en
locale=en-US
i18n_redirected=en
preferred_language=en-US
_language=en
site_language=en
```

### Setting Cookies in Crawlers

**Playwright:**

```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    context = browser.new_context(
        locale='en-US',  # Browser locale emulation
        extra_http_headers={
            'Accept-Language': 'en-US, en;q=0.9'
        }
    )

    # Add language cookie before navigation
    context.add_cookies([{
        'name': 'lang',
        'value': 'en',
        'domain': '.example.com',
        'path': '/'
    }])

    page = context.new_page()
    page.goto('https://example.com')
```

**Firecrawl (via headers):**

```python
# Firecrawl API allows custom headers including Cookie
params = {
    "scrapeOptions": {
        "formats": ["markdown"],
        "headers": {
            "Accept-Language": "en-US, en;q=0.9",
            "Cookie": "lang=en; locale=en-US"
        }
    }
}
```

### Best Practices

1. **Inspect target site first** - Check which cookie controls language (DevTools → Application → Cookies)
2. **Set cookie + header** - Redundancy ensures coverage (some sites use one or both)
3. **Match cookie scope** - Set correct `domain` and `path` (wildcard domains start with `.`)
4. **Cookie persistence** - Some sites require persistent cookies across requests

---

## Query Parameter Approaches

Less common but still used for language selection.

### Common Patterns

```
https://example.com/page?lang=en
https://example.com/page?language=en
https://example.com/page?hl=en (Google-style)
https://example.com/page?locale=en-US
https://example.com/page?i18n=en
```

### Implementation

**Append to base URL:**

```python
from urllib.parse import urlencode, urlparse, parse_qs, urlunparse

def add_language_param(url: str, lang: str = "en") -> str:
    """Add language query parameter to URL."""
    parsed = urlparse(url)
    query_params = parse_qs(parsed.query)
    query_params['lang'] = [lang]  # Override if exists

    new_query = urlencode(query_params, doseq=True)
    return urlunparse(parsed._replace(query=new_query))

# Usage
url = add_language_param("https://example.com/docs", "en")
# → https://example.com/docs?lang=en
```

**Drawbacks:**

- Not SEO-friendly (search engines prefer path-based)
- Can conflict with other query parameters
- Often ignored by sites with cookies/headers

---

## Preventing Auto-Redirects

### Problem Statement

Many multilingual sites auto-detect user location via:
1. **IP geolocation** - Redirects based on IP address country
2. **Accept-Language header** - Redirects based on browser language
3. **Cookies** - Remembers previous language choice
4. **User-Agent** - Detects mobile/desktop and language preferences

**Example redirect chains:**

```
https://example.com/docs
  → 302 https://example.com/de/docs (IP from Germany)
  → 200 (German content)
```

### Strategies to Prevent Auto-Redirects

#### 1. Explicit English URLs

**Force English path:**

```python
# Bad: Root URL may redirect
url = "https://example.com/docs"

# Good: Explicit English path
url = "https://example.com/en/docs"
```

#### 2. Header Combination (Defense-in-Depth)

**Send all language signals as English:**

```python
headers = {
    'Accept-Language': 'en-US, en;q=0.9',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Cookie': 'lang=en; locale=en-US; i18n_redirected=en',
    'Referer': 'https://example.com/en/'  # Suggest English context
}
```

#### 3. Disable Redirect Following (Advanced)

**Detect and handle redirects manually:**

```python
import requests

response = requests.get(
    url,
    headers={'Accept-Language': 'en-US'},
    allow_redirects=False  # Don't auto-follow
)

if response.status_code in (301, 302, 303, 307, 308):
    redirect_url = response.headers['Location']

    # Check if redirected to non-English locale
    if '/de/' in redirect_url or '/fr/' in redirect_url:
        # Force English version
        redirect_url = redirect_url.replace('/de/', '/en/')
        redirect_url = redirect_url.replace('/fr/', '/en/')

    response = requests.get(redirect_url, headers=headers)
```

#### 4. VPN/Proxy Location Matching

**Use proxies in English-speaking regions:**

```python
# Use US/UK proxies to avoid geolocation redirects
proxies = {
    'http': 'http://us-proxy.example.com:8080',
    'https': 'http://us-proxy.example.com:8080'
}

response = requests.get(url, proxies=proxies, headers=headers)
```

**Firecrawl proxy configuration:**

```python
params = {
    "scrapeOptions": {
        "formats": ["markdown"],
        "location": {
            "country": "US",  # Force US location
            "languages": ["en-US"]
        }
    }
}
```

#### 5. Playwright Navigation Options

**Wait for final URL before scraping:**

```python
page.goto(url, wait_until='networkidle')

# Check final URL after redirects
final_url = page.url
if '/en/' not in final_url:
    # Redirect to English version
    en_url = final_url.replace(page.url.split('/')[3], 'en')
    page.goto(en_url)
```

---

## Implementation Patterns

### Pattern 1: Header-First Approach (Recommended)

**Best for:** Most sites with Accept-Language support

```python
def crawl_with_language(url: str, lang: str = "en") -> str:
    """Crawl with explicit language control via headers."""

    headers = {
        'Accept-Language': f'{lang}-US, {lang};q=0.9',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',  # Do Not Track
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }

    response = requests.get(url, headers=headers, timeout=30)
    return response.text
```

### Pattern 2: Cookie + Header Combination

**Best for:** Sites with persistent language selection

```python
def crawl_with_cookie_language(url: str, lang: str = "en") -> str:
    """Crawl with cookie + header language control."""

    session = requests.Session()

    # Set language cookie
    session.cookies.set('lang', lang, domain='.example.com')
    session.cookies.set('locale', f'{lang}-US', domain='.example.com')

    # Set headers
    session.headers.update({
        'Accept-Language': f'{lang}-US, {lang};q=0.9',
        'User-Agent': 'Mozilla/5.0 ...'
    })

    response = session.get(url)
    return response.text
```

### Pattern 3: URL Rewriting

**Best for:** Sites with strict URL-based routing

```python
def force_english_url(url: str) -> str:
    """Rewrite URL to force English locale."""

    # Remove existing locale prefixes
    locales = ['de', 'fr', 'es', 'it', 'pt', 'ja', 'zh', 'ko']

    parsed = urlparse(url)
    parts = parsed.path.strip('/').split('/')

    # Remove first part if it's a known locale
    if parts and parts[0] in locales:
        parts.pop(0)

    # Inject 'en' at start
    if parts[0] != 'en':
        parts.insert(0, 'en')

    new_path = '/' + '/'.join(parts)
    return parsed._replace(path=new_path).geturl()

# Usage
url = force_english_url("https://example.com/de/docs")
# → https://example.com/en/docs
```

### Pattern 4: Playwright Full Control

**Best for:** Complex JavaScript-heavy sites with dynamic redirects

```python
from playwright.sync_api import sync_playwright

def crawl_with_playwright(url: str, lang: str = "en") -> str:
    """Crawl with full browser emulation and language control."""

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        # Create context with locale emulation
        context = browser.new_context(
            locale=f'{lang}-US',
            timezone_id='America/New_York',
            extra_http_headers={
                'Accept-Language': f'{lang}-US, {lang};q=0.9'
            }
        )

        # Set language cookies before navigation
        context.add_cookies([
            {'name': 'lang', 'value': lang, 'domain': '.example.com', 'path': '/'},
            {'name': 'locale', 'value': f'{lang}-US', 'domain': '.example.com', 'path': '/'}
        ])

        page = context.new_page()

        # Navigate and wait for network idle
        page.goto(url, wait_until='networkidle', timeout=30000)

        # Verify final URL is English
        final_url = page.url
        if f'/{lang}/' not in final_url and f'{lang}.' not in final_url:
            # Try explicit English URL
            if '/en/' not in url:
                en_url = url.replace(urlparse(url).path, f'/en{urlparse(url).path}')
                page.goto(en_url, wait_until='networkidle')

        content = page.content()

        browser.close()
        return content
```

---

## Firecrawl-Specific Configuration

Based on Firecrawl v2 API documentation and existing Taboot implementation.

### Current Implementation (Taboot WebReader)

**Location:** `/home/jmagar/code/taboot/packages/ingest/readers/web.py`

```python
class WebReader:
    def load_data(self, url: str, limit: int | None = None) -> list[Document]:
        params: dict[str, object] = {
            "scrape_options": {
                "formats": ["markdown"]
            }
        }
        if limit is not None:
            params["limit"] = limit

        reader = FireCrawlWebReader(
            api_key=self.firecrawl_api_key,
            api_url=self.firecrawl_url,
            mode="crawl",
            params=params,
        )

        docs = reader.load_data(url=url)
        return docs
```

### Enhanced Configuration with Language Control

```python
class WebReader:
    def load_data(
        self,
        url: str,
        limit: int | None = None,
        language: str = "en",
        location_country: str = "US"
    ) -> list[Document]:
        """Load documents with language and location control.

        Args:
            url: URL to crawl
            limit: Maximum pages to crawl
            language: Target language code (default: "en")
            location_country: Country code for proxy location (default: "US")

        Returns:
            List of LlamaIndex Document objects
        """

        # Build scrape options with language control
        params: dict[str, object] = {
            "scrape_options": {
                "formats": ["markdown"],
                "headers": {
                    "Accept-Language": f"{language}-{location_country}, {language};q=0.9",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9",
                },
                # Use location settings (Firecrawl v2)
                "location": {
                    "country": location_country,
                    "languages": [f"{language}-{location_country}"]
                },
                # Default Firecrawl v2 options
                "onlyMainContent": True,
                "blockAds": True,
                "skipTlsVerification": True,
                "removeBase64Images": True,
                "maxAge": 172800000  # 2 days cache
            }
        }

        if limit is not None:
            params["limit"] = limit

        # Use stealth proxy for sites with aggressive geo-detection
        params["scrape_options"]["proxy"] = "stealth"  # or "basic" or "auto"

        reader = FireCrawlWebReader(
            api_key=self.firecrawl_api_key,
            api_url=self.firecrawl_url,
            mode="crawl",
            params=params,
        )

        docs = reader.load_data(url=url)

        # Add language metadata
        for doc in docs:
            if not doc.metadata:
                doc.metadata = {}
            doc.metadata["source_url"] = url
            doc.metadata["language"] = language
            doc.metadata["location_country"] = location_country

        return docs
```

### Configuration Options Reference

**Firecrawl v2 API - Location Object:**

```json
{
  "location": {
    "country": "US",      // ISO 3166-1 alpha-2 country code
    "languages": ["en-US"] // Preferred languages for the location
  }
}
```

**Supported location countries:**
- `"US"` - United States
- `"GB"` - United Kingdom
- `"CA"` - Canada
- `"AU"` - Australia
- `"DE"` - Germany
- `"FR"` - France
- `"JP"` - Japan
- (check Firecrawl docs for full list)

**Proxy modes:**
- `"basic"` - Fast, basic anti-bot (default for most sites)
- `"stealth"` - Advanced anti-bot, residential proxies (costs 5 credits)
- `"auto"` - Tries basic first, falls back to stealth if needed

---

## Playwright Browser Emulation

Based on official Playwright documentation: https://playwright.dev/docs/emulation

### Locale and Timezone Configuration

```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()

    context = browser.new_context(
        # Emulate US English locale
        locale='en-US',

        # Set timezone
        timezone_id='America/New_York',

        # Set geolocation (requires permissions)
        geolocation={'longitude': -73.935242, 'latitude': 40.730610},
        permissions=['geolocation'],

        # Custom headers
        extra_http_headers={
            'Accept-Language': 'en-US, en;q=0.9',
            'Accept': 'text/html,application/xhtml+xml',
        }
    )

    page = context.new_page()
    page.goto('https://example.com')
```

### Available Locale Values

Playwright supports any valid BCP 47 language tag:

**Common English variants:**
- `en-US` - US English
- `en-GB` - British English
- `en-CA` - Canadian English
- `en-AU` - Australian English

**Other languages:**
- `de-DE` - German
- `fr-FR` - French
- `es-ES` - Spanish
- `ja-JP` - Japanese
- `zh-CN` - Simplified Chinese
- `zh-TW` - Traditional Chinese

### Device Emulation with Locale

```python
from playwright.sync_api import sync_playwright, devices

# Use preset device with custom locale
iphone_13 = devices['iPhone 13']

with sync_playwright() as p:
    browser = p.webkit.launch()

    context = browser.new_context(
        **iphone_13,
        locale='en-US',  # Override device default
        timezone_id='America/Los_Angeles'
    )

    page = context.new_page()
    page.goto('https://example.com')
```

---

## Recommendations for Taboot

### Short-Term (Immediate Implementation)

1. **Add language parameters to WebReader:**

```python
# packages/ingest/readers/web.py
class WebReader:
    def __init__(
        self,
        firecrawl_url: str,
        firecrawl_api_key: str,
        rate_limit_delay: float = 1.0,
        max_retries: int = 3,
        default_language: str = "en",
        default_location: str = "US",
    ):
        # ... existing init code ...
        self.default_language = default_language
        self.default_location = default_location

    def load_data(
        self,
        url: str,
        limit: int | None = None,
        language: str | None = None,
        location: str | None = None,
    ) -> list[Document]:
        # Use defaults if not specified
        lang = language or self.default_language
        loc = location or self.default_location

        # Build params with language control
        params = {
            "scrape_options": {
                "formats": ["markdown"],
                "headers": {
                    "Accept-Language": f"{lang}-{loc}, {lang};q=0.9"
                },
                "location": {
                    "country": loc,
                    "languages": [f"{lang}-{loc}"]
                }
            }
        }
        # ... rest of method
```

2. **Add CLI flags:**

```python
# apps/cli/taboot_cli/commands/ingest_web.py
@app.command(name="web")
def ingest_web_command(
    url: Annotated[str, typer.Argument(..., help="URL to crawl and ingest")],
    limit: Annotated[int | None, typer.Option(...)] = None,
    language: Annotated[str, typer.Option("--lang", help="Language code (e.g., en, de, fr)")] = "en",
    location: Annotated[str, typer.Option("--location", help="Country code (e.g., US, GB, DE)")] = "US",
):
    """Ingest web documents with language control."""
    # ... existing setup code ...

    web_reader = WebReader(
        firecrawl_url=config.firecrawl_api_url,
        firecrawl_api_key=config.firecrawl_api_key.get_secret_value(),
        default_language=language,
        default_location=location,
    )

    # ... rest of command
```

**Usage:**

```bash
# Crawl in English (default)
uv run apps/cli ingest web https://example.com

# Crawl in German from Germany
uv run apps/cli ingest web https://example.com --lang de --location DE

# Crawl in Japanese from Japan
uv run apps/cli ingest web https://example.com --lang ja --location JP
```

### Medium-Term (Next Sprint)

1. **Add configuration to .env:**

```bash
# .env
# Default language/location for web crawling
DEFAULT_CRAWL_LANGUAGE=en
DEFAULT_CRAWL_LOCATION=US

# Force English URLs (rewrite URLs to /en/ prefix)
FORCE_ENGLISH_URLS=true
```

2. **URL rewriting for known multilingual sites:**

```python
# packages/ingest/readers/web.py
class WebReader:
    def _normalize_url_locale(self, url: str, target_lang: str) -> str:
        """Rewrite URL to target language if possible."""

        if not self.config.force_english_urls:
            return url

        parsed = urlparse(url)
        path_parts = parsed.path.strip('/').split('/')

        # Known locale codes to replace
        locales = ['de', 'fr', 'es', 'it', 'pt', 'ja', 'zh', 'ko', 'ru', 'ar']

        if path_parts and path_parts[0] in locales:
            path_parts[0] = target_lang
        elif path_parts and path_parts[0] != target_lang:
            path_parts.insert(0, target_lang)

        new_path = '/' + '/'.join(path_parts)
        return parsed._replace(path=new_path).geturl()
```

### Long-Term (Future Considerations)

1. **Automatic language detection:**

```python
from langdetect import detect_langs

def validate_content_language(content: str, expected_lang: str) -> bool:
    """Verify scraped content matches expected language."""
    detected = detect_langs(content[:1000])  # Check first 1000 chars

    for lang_prob in detected:
        if lang_prob.lang == expected_lang and lang_prob.prob > 0.8:
            return True

    return False
```

2. **Retry with URL rewriting if language mismatch:**

```python
def load_data_with_validation(self, url: str, language: str) -> list[Document]:
    """Load data and retry with URL rewriting if language mismatch."""

    docs = self.load_data(url, language=language)

    # Check first document
    if docs and not validate_content_language(docs[0].text, language):
        logger.warning(f"Language mismatch detected for {url}, retrying with URL rewrite")

        # Try explicit language URL
        rewritten_url = self._normalize_url_locale(url, language)
        if rewritten_url != url:
            docs = self.load_data(rewritten_url, language=language)

    return docs
```

3. **Per-domain language configuration:**

```yaml
# config/domain_languages.yaml
domains:
  - domain: example.com
    default_language: en
    url_pattern: path_based  # or subdomain, tld
    locale_prefix: true

  - domain: docs.example.com
    default_language: en
    url_pattern: subdomain
    redirect_aggressive: true
    cookies: ["lang", "locale"]
```

---

## References

### Official Documentation

1. **HTTP Accept-Language**: [MDN Web Docs - Accept-Language](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Accept-Language)
2. **RFC 9110 (HTTP Semantics)**: [HTTP Content Negotiation](https://httpwg.org/specs/rfc9110.html#field.accept-language)
3. **Playwright Emulation**: [Playwright Docs - Emulation](https://playwright.dev/docs/emulation)
4. **Firecrawl API v2**: [Firecrawl API Reference - Scrape Endpoint](https://docs.firecrawl.dev/api-reference/endpoint/scrape)
5. **BCP 47 Language Tags**: [IETF RFC 5646](https://datatracker.ietf.org/doc/html/rfc5646)

### Industry Best Practices

1. **W3C Internationalization**: [Language Negotiation](https://www.w3.org/International/questions/qa-accept-lang-locales)
2. **Google Webmaster Guidelines**: [Managing Multi-Regional Sites](https://developers.google.com/search/docs/specialty/international/managing-multi-regional-sites)
3. **OWASP Web Security**: [Content Negotiation](https://owasp.org/www-community/vulnerabilities/Content_Negotiation)

### Code Examples & Libraries

1. **Scrapy Language Middleware**: [scrapy-language-middleware](https://github.com/scrapy-plugins/scrapy-language-middleware)
2. **Playwright Python**: [Browser Context API](https://playwright.dev/python/docs/api/class-browsercontext)
3. **LlamaIndex Firecrawl Reader**: [FireCrawlWebReader](https://docs.llamaindex.ai/en/latest/examples/data_connectors/WebPageDemo/#using-firecrawl-reader)

---

## Appendix A: Language Code Reference

### ISO 639-1 Two-Letter Codes (Common)

| Code | Language | Example Region |
|------|----------|----------------|
| `en` | English | US, GB, CA, AU |
| `de` | German | DE, AT, CH |
| `fr` | French | FR, CA, BE |
| `es` | Spanish | ES, MX, AR |
| `it` | Italian | IT, CH |
| `pt` | Portuguese | PT, BR |
| `ja` | Japanese | JP |
| `zh` | Chinese | CN, TW, HK |
| `ko` | Korean | KR |
| `ru` | Russian | RU |
| `ar` | Arabic | SA, EG, AE |
| `nl` | Dutch | NL, BE |
| `pl` | Polish | PL |
| `tr` | Turkish | TR |
| `sv` | Swedish | SE |
| `da` | Danish | DK |
| `no` | Norwegian | NO |
| `fi` | Finnish | FI |

### ISO 3166-1 Alpha-2 Country Codes (Common)

| Code | Country |
|------|---------|
| `US` | United States |
| `GB` | United Kingdom |
| `CA` | Canada |
| `AU` | Australia |
| `DE` | Germany |
| `FR` | France |
| `ES` | Spain |
| `IT` | Italy |
| `JP` | Japan |
| `CN` | China |
| `KR` | South Korea |
| `BR` | Brazil |
| `MX` | Mexico |
| `IN` | India |
| `RU` | Russia |

---

## Appendix B: Common Redirect Detection Patterns

### JavaScript-Based Redirects

```javascript
// Detect common JS redirect patterns
window.location.href = '/de/page';
window.location.replace('/de/page');
window.location.assign('/de/page');
document.location = '/de/page';

// Meta refresh
<meta http-equiv="refresh" content="0;url=/de/page">
```

### Server-Side Redirect Headers

```http
HTTP/1.1 302 Found
Location: /de/page
Vary: Accept-Language

HTTP/1.1 301 Moved Permanently
Location: https://de.example.com/page
```

### Playwright Detection

```python
def detect_language_redirect(page):
    """Detect if page was redirected based on language."""

    # Check redirect chain
    initial_url = page.url

    # Wait for potential JS redirects
    page.wait_for_load_state('networkidle', timeout=5000)

    final_url = page.url

    if initial_url != final_url:
        # Extract locale from URL path
        initial_locale = extract_locale_from_url(initial_url)
        final_locale = extract_locale_from_url(final_url)

        if initial_locale != final_locale:
            return {
                'redirected': True,
                'from_locale': initial_locale,
                'to_locale': final_locale,
                'from_url': initial_url,
                'to_url': final_url
            }

    return {'redirected': False}
```

---

## Appendix C: Testing Language Control

### Test Suite for Language Headers

```python
import pytest
from packages.ingest.readers.web import WebReader

@pytest.fixture
def web_reader(config):
    return WebReader(
        firecrawl_url=config.firecrawl_api_url,
        firecrawl_api_key=config.firecrawl_api_key,
        default_language="en",
        default_location="US",
    )

def test_english_language_default(web_reader):
    """Test that default language is English."""
    docs = web_reader.load_data("https://example.com/docs")

    assert len(docs) > 0
    assert docs[0].metadata.get("language") == "en"

def test_german_language_override(web_reader):
    """Test crawling with German language override."""
    docs = web_reader.load_data(
        "https://example.com/docs",
        language="de",
        location="DE"
    )

    assert len(docs) > 0
    assert docs[0].metadata.get("language") == "de"
    assert docs[0].metadata.get("location_country") == "DE"

def test_url_locale_rewriting(web_reader):
    """Test that URLs are rewritten to English."""
    original_url = "https://example.com/de/docs"
    expected_url = "https://example.com/en/docs"

    normalized = web_reader._normalize_url_locale(original_url, "en")
    assert normalized == expected_url

@pytest.mark.integration
def test_language_validation(web_reader):
    """Test that content language matches requested language."""
    docs = web_reader.load_data(
        "https://example.com/docs",
        language="en"
    )

    # Check that content is actually in English
    from langdetect import detect
    detected_lang = detect(docs[0].text[:500])
    assert detected_lang == "en"
```

### Manual Testing Commands

```bash
# Test with curl
curl -v https://example.com/docs \
  -H "Accept-Language: en-US, en;q=0.9" \
  -H "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64)" \
  | grep -i "location:"

# Test with Firecrawl API directly
curl -X POST https://api.firecrawl.dev/v2/scrape \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer YOUR_API_KEY' \
  -d '{
    "url": "https://example.com/docs",
    "formats": ["markdown"],
    "location": {
      "country": "US",
      "languages": ["en-US"]
    },
    "headers": {
      "Accept-Language": "en-US, en;q=0.9"
    }
  }'

# Test with Taboot CLI (after implementation)
uv run apps/cli ingest web https://example.com/docs --lang en --location US
```

---

## Version History

- **v1.0** (2025-01-XX) - Initial documentation based on MDN, RFC 9110, Playwright, and Firecrawl v2 API research
