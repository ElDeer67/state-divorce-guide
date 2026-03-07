#!/usr/bin/env python3
"""Rebuild all divorce guide pages with editorial design."""

import os, re, glob

FEATURED_IMAGES = [
    ("https://images.unsplash.com/photo-1450101499163-c8848c66ca85?w=1400&q=80", "Reviewing legal documents"),
    ("https://images.unsplash.com/photo-1589829545856-d10d557cf95f?w=1400&q=80", "Legal paperwork and gavel"),
    ("https://images.unsplash.com/photo-1521791055366-0d553872125f?w=1400&q=80", "Legal consultation"),
    ("https://images.unsplash.com/photo-1507679799987-c73779587ccf?w=1400&q=80", "Professional meeting"),
    ("https://images.unsplash.com/photo-1454165804606-c3d57bc86b40?w=1400&q=80", "Reviewing paperwork"),
    ("https://images.unsplash.com/photo-1573164713714-d95e436ab8d6?w=1400&q=80", "Working on documents"),
    ("https://images.unsplash.com/photo-1423592707957-3b212afa6733?w=1400&q=80", "Pen on legal forms"),
    ("https://images.unsplash.com/photo-1556761175-b413da4baf72?w=1400&q=80", "Team collaboration"),
    ("https://images.unsplash.com/photo-1600880292203-757bb62b4baf?w=1400&q=80", "Business meeting"),
    ("https://images.unsplash.com/photo-1542744173-8e7e53415bb0?w=1400&q=80", "Presentation"),
    ("https://images.unsplash.com/photo-1553877522-43269d4ea984?w=1400&q=80", "Planning session"),
    ("https://images.unsplash.com/photo-1524758631624-e2822e304c36?w=1400&q=80", "Workspace"),
]

INLINE_IMAGES = [
    ("https://images.unsplash.com/photo-1450101499163-c8848c66ca85?w=700&q=80", "Reviewing legal documents at desk"),
    ("https://images.unsplash.com/photo-1589829545856-d10d557cf95f?w=700&q=80", "Legal paperwork"),
    ("https://images.unsplash.com/photo-1507679799987-c73779587ccf?w=700&q=80", "Professional consultation"),
    ("https://images.unsplash.com/photo-1554224155-6726b3ff858f?w=700&q=80", "Financial documents review"),
    ("https://images.unsplash.com/photo-1573164713714-d95e436ab8d6?w=700&q=80", "Working at laptop"),
    ("https://images.unsplash.com/photo-1521791055366-0d553872125f?w=700&q=80", "Signing documents"),
    ("https://images.unsplash.com/photo-1423592707957-3b212afa6733?w=700&q=80", "Pen and forms"),
    ("https://images.unsplash.com/photo-1556761175-4b46a572b786?w=700&q=80", "Meeting with advisor"),
    ("https://images.unsplash.com/photo-1454165804606-c3d57bc86b40?w=700&q=80", "Reviewing important papers"),
    ("https://images.unsplash.com/photo-1600880292203-757bb62b4baf?w=700&q=80", "Professional discussion"),
]

def slug_to_name(slug):
    parts = slug.replace("-", " ").split()
    exceptions = {"of": "of", "the": "the"}
    return " ".join(exceptions.get(p, p.capitalize()) for p in parts)

def strip_related_guides(html):
    """Remove all duplicated 'Related State Guides' blocks."""
    return re.sub(
        r'\s*<div style="background: #f8f9fa; padding: 2rem.*?Related State Guides.*?</div>\s*</div>',
        '', html, flags=re.DOTALL
    )

def strip_ad_slots(html):
    # Ad slots may not have closing tags (broken HTML), remove the opener and its text content
    html = re.sub(r'<div class="ad-slot">\s*\[.*?\]\s*', '', html, flags=re.DOTALL)
    # Also try standard closing
    html = re.sub(r'<div class="ad-slot">.*?</div>', '', html, flags=re.DOTALL)
    return html

def extract_meta(html):
    title = ""
    desc = ""
    m = re.search(r'<title>(.*?)</title>', html, re.DOTALL)
    if m: title = m.group(1).strip()
    m = re.search(r'name="description"\s+content="(.*?)"', html, re.DOTALL)
    if m: desc = m.group(1).strip()
    return title, desc

def extract_canonical(html):
    m = re.search(r'<link\s+rel="canonical"\s+href="(.*?)"', html)
    return m.group(1) if m else ""

def extract_h1(html):
    m = re.search(r'<h1>(.*?)</h1>', html, re.DOTALL)
    return m.group(1).strip() if m else ""

def extract_stats(html):
    """Extract stat-card values."""
    stats = []
    for m in re.finditer(r'<div class="number">(.*?)</div>.*?<div class="label">(.*?)</div>', html, re.DOTALL):
        stats.append((m.group(2).strip(), m.group(1).strip()))
    return stats

def extract_body(html):
    """Extract main content body."""
    # Try container > content first
    m = re.search(r'<div class="container">\s*<div class="content">(.*?)</div>\s*</div>\s*<footer>', html, re.DOTALL)
    if m:
        return m.group(1)
    # Fallback
    m = re.search(r'<div class="container">(.*?)<footer>', html, re.DOTALL)
    if m:
        return m.group(1)
    return ""

def extract_one_schema(html, schema_type):
    m = re.search(
        r'<script type="application/ld\+json">\s*\{[^}]*"@type":\s*"' + schema_type + r'".*?\}\s*</script>',
        html, re.DOTALL
    )
    return m.group(0) if m else ""

def clean_body(body):
    body = re.sub(r'\s*style="[^"]*"', '', body)
    body = strip_ad_slots(body)
    # Remove the old .content wrapper div
    body = re.sub(r'<div class="content">\s*', '', body)
    # Remove any remaining stray closing divs by balancing
    # First pass: remove excess openers for known wrapper classes
    # Final pass: balance by removing unmatched opens/closes
    lines = body.split('\n')
    result = []
    depth = 0
    for line in lines:
        opens = len(re.findall(r'<div\b', line))
        closes = len(re.findall(r'</div>', line))
        new_depth = depth + opens - closes
        if new_depth < 0 and re.match(r'^\s*</div>\s*$', line):
            new_depth += 1
            continue
        depth = new_depth
        result.append(line)
    body = '\n'.join(result)
    # If still unbalanced (more opens than closes), add closing divs
    opens = len(re.findall(r'<div\b', body))
    closes = len(re.findall(r'</div>', body))
    if opens > closes:
        body += '\n' + '</div>\n' * (opens - closes)
    return body.strip()

def add_photos(body, state_slug):
    """Insert 2 photos into the body content at natural break points."""
    idx = hash(state_slug) % len(INLINE_IMAGES)
    img1_url, img1_alt = INLINE_IMAGES[idx % len(INLINE_IMAGES)]
    img2_url, img2_alt = INLINE_IMAGES[(idx + 3) % len(INLINE_IMAGES)]
    
    # Insert first photo after first h2
    h2_match = re.search(r'(</h2>.*?</p>)', body, re.DOTALL)
    if h2_match:
        insert_pos = h2_match.end()
        photo1 = f'\n\n            <img src="{img1_url}" alt="{img1_alt}" class="content-image">\n'
        body = body[:insert_pos] + photo1 + body[insert_pos:]
    
    # Insert second photo after "Cost" or "How Long" h2
    h2_matches = list(re.finditer(r'<h2[^>]*>.*?(?:Cost|How Long|How Much|Timeline).*?</h2>', body, re.DOTALL | re.IGNORECASE))
    if h2_matches:
        m = h2_matches[0]
        # Find next paragraph after this h2
        next_p = re.search(r'</p>', body[m.end():])
        if next_p:
            insert_pos2 = m.end() + next_p.end()
            photo2 = f'\n\n            <img src="{img2_url}" alt="{img2_alt}" class="content-image">\n'
            body = body[:insert_pos2] + photo2 + body[insert_pos2:]
    
    return body

def build_page(title, desc, canonical, h1, stats, body, schemas, state_name, featured_img, featured_alt):
    facts_html = ""
    for label, value in stats:
        facts_html += f'            <div class="fact"><div class="fact-label">{label}</div><div class="fact-value">{value}</div></div>\n'
    
    canonical_tag = f'    <link rel="canonical" href="{canonical}">\n' if canonical else ""
    
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <script async src="https://www.googletagmanager.com/gtag/js?id=G-QFF1KGPLQT"></script>
    <script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments)}};gtag('js',new Date());gtag('config','G-QFF1KGPLQT');</script>
{schemas}    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="{desc}">
{canonical_tag}    <title>{title}</title>
    <link rel="stylesheet" href="/style.css">
</head>
<body>
    <nav class="site-nav">
        <a href="/" class="logo">StatesDivorceGuide</a>
        <div class="nav-links">
            <a href="/privacy-policy">Privacy Policy</a>
        </div>
    </nav>

    <div class="breadcrumbs">
        <a href="/">Home</a><span class="sep">&rsaquo;</span>
        {state_name} Divorce
    </div>

    <div class="featured-img">
        <img src="{featured_img}" alt="{featured_alt}">
        <div class="caption">Filing for divorce in {state_name}</div>
    </div>

    <div class="article-header">
        <h1>{h1}</h1>
        <p class="byline">By <strong>StatesDivorceGuide Staff</strong> &middot; Updated March 2026</p>
    </div>

    <div class="quick-facts">
        <div class="quick-facts-inner">
{facts_html}        </div>
    </div>

    <div class="article-body">
{body}
    </div>

    <footer>
        <div class="footer-links">
            <a href="/">Home</a>
            <a href="/privacy-policy">Privacy Policy</a>
        </div>
        <p>&copy; 2026 StatesDivorceGuide.com &middot; Free divorce guides for all 50 states.</p>
        <p>This guide is for informational purposes only. Consult a licensed attorney for advice specific to your situation.</p>
    </footer>
</body>
</html>'''


def process_file(filepath):
    filename = os.path.basename(filepath)
    state_slug = filename.replace("-divorce.html", "")
    state_name = slug_to_name(state_slug)
    
    with open(filepath) as f:
        html = f.read()
    
    # Clean duplicated junk
    html = strip_related_guides(html)
    
    title, desc = extract_meta(html)
    canonical = extract_canonical(html)
    h1_text = extract_h1(html)
    body = extract_body(html)
    body = clean_body(body)
    body = add_photos(body, state_slug)
    
    # Extract schemas (one each)
    howto = extract_one_schema(html, "HowTo")
    faq = extract_one_schema(html, "FAQPage")
    schemas = ""
    if howto: schemas += f"    {howto}\n"
    if faq: schemas += f"    {faq}\n"
    
    img_idx = hash(state_slug) % len(FEATURED_IMAGES)
    featured_img, featured_alt = FEATURED_IMAGES[img_idx]
    
    new_html = build_page(
        title, desc, canonical, h1_text, [], body, schemas,
        state_name, featured_img, featured_alt
    )
    
    with open(filepath, 'w') as f:
        f.write(new_html)
    
    print(f"  Rebuilt: {filename} ({state_name})")


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    files = sorted([f for f in glob.glob("*-divorce.html") if not f.startswith("blog")])
    print(f"Found {len(files)} state pages to rebuild.\n")
    for f in files:
        try:
            process_file(f)
        except Exception as e:
            print(f"  ERROR on {f}: {e}")
    print(f"\nDone. Rebuilt {len(files)} pages.")
