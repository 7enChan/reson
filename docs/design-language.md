# Reson Design Language

## Direction

- Name: warm audio workbench
- Archetype: sharp transactional utility with dense operational dashboard discipline
- Site type: local product utility / dashboard
- Audience: users converting EPUB or Markdown manuscripts into audiobook output
- Impression in 5 seconds: calm, capable, and focused on production controls
- What must feel true: this is a tool for long-running audio generation, not a marketing page
- Primary user task: choose a TTS engine, upload a book, tune voice/output options, and start generation
- Main risk if the design is wrong: the UI feels decorative or generic and makes advanced controls harder to scan

## Brand / VI Audit

- Existing logo or wordmark: text-only `Reson`
- Logo shape language: heavy, rounded word rhythm; no icon asset in the repo
- Logo constraints: use the wordmark plainly; avoid adding an invented symbol until a real mark exists
- Existing primary color: warm sand/gold from the current primary CTA (`#e8c48b`)
- Existing secondary color: cool blue-gray sidebar and input surfaces
- Existing accent color: provisional amber (`#d59b48`) for interactive progress and primary actions
- Existing neutral palette: paper white, soft blue-gray panels, ink text, low-contrast dividers
- Semantic colors: green for success, amber for warning, red for errors, blue for info
- Proposed VI direction: a warm, editorial audio workbench with precise utility controls
- Why this VI fits the product: audiobook generation is creative but operational; controls need calm hierarchy and predictable states
- What this site must not be mistaken for: a SaaS landing page, a social audio app, or a decorative AI demo
- Reference inputs used: current Streamlit UI, user screenshot, existing README/product behavior, existing warm CTA color
- Reference inputs rejected and why: generic purple/blue gradient SaaS styling; it conflicts with the quiet local-tool workflow

## Product Site Decision

- Primary subject: product utility
- Main visitor question: can I configure and run an audiobook generation job clearly?
- Main credibility proof: supported provider/options are represented as real controls, not invented claims
- Main conversion action: `开始制作`
- Product role on this site: the app is the product surface
- Investor/partner role on this site: none
- Navigation priority: engine settings in the sidebar, generation inputs and outputs in the main pane
- Above-fold priority: wordmark, input setup, output setup, and primary run action

## Tokens

### Color

- Background: `#fbfaf7`
- Background alternate: `#eef1f5`
- Surface: `#ffffff`
- Surface raised: `#fffdf9`
- Surface subtle: `#f1f3f7`
- Text primary: `#252838`
- Text secondary: `#5f6472`
- Text muted: `#858b99`
- Border: `#d9d6cf`
- Border strong: `#bdb7aa`
- Brand primary: `#d59b48` / slider fill, focused controls, key interaction states
- Brand secondary: `#2f5d6c` / reserved support color for future status or grouping
- Accent: `#e8c48b` / primary CTA fill and warm highlights
- Accent soft: `#f5ead8` / subtle selected or hover backgrounds
- Success: `#2f8a5b` / successful task messages
- Warning: `#b97817` / caution states
- Error: `#b84a3c` / errors and destructive states
- Info: `#3d6f8e` / neutral process information
- Contrast notes: CTA text should stay near-black; muted text must not fall below readable contrast on gray panels

### Typography

- Display: system sans, heavy weight, tight but non-negative tracking
- H1: 3.8rem desktop, 2.6rem mobile, 800 weight, line-height 1.0
- H2/H3: compact section labels, 700 weight
- Body: system sans, 1rem, line-height 1.5
- Metadata: 0.9rem, medium weight, muted color
- Data/number: tabular numerals where possible
- Link: brand primary with underline on hover
- Line-height rules: controls stay compact; long helper/log text can use relaxed line-height
- Max text width: main content remains under 1120px; prose captions stay under 720px

### Geometry

- Page width: 640px max content width for the main workbench
- Content width: main pane centered with generous left alignment
- Grid: Streamlit columns, with mobile collapse to one column
- Section spacing: 2.25rem between major groups, 0.9rem inside control groups
- Card padding: avoid decorative cards; use native form surfaces and expander panels
- Radius: 10px for inputs/buttons, 14px for larger upload/drop surfaces
- Border: 1px soft neutral divider
- Shadow: minimal, only focus/hover lift on actionable controls
- Sticky/fixed elements: keep Streamlit sidebar behavior; do not add sticky action bars yet
- Mobile breakpoints: reduce page padding, compact H1, avoid multi-column assumptions

## Visual Identity Rules

- Logo usage: `Reson` appears as a plain wordmark; do not pair it with an invented icon
- Palette usage: neutral system first, warm amber only for intent and state
- Icon style: use Streamlit/native icons only; avoid mixed custom icon packs
- Image/video style: no decorative stock imagery in the app shell
- Illustration style: none unless a real product diagram is needed
- Data visualization style: quiet labels, semantic color only when data/status exists
- What should repeat across pages: input geometry, warm primary action, slim dividers, compact labels
- What should never repeat: red default sliders, nested card stacks, decorative gradients, fake metrics

## Components

### Navigation

- Structure: sidebar owns engine/provider configuration
- Active state: selected controls use brand primary or accent-soft, not default red
- CTA placement: generation action stays after input/output settings
- Mobile behavior: sidebar can collapse; main controls must remain usable in one column
- Scroll behavior: no animated or sticky decoration

### Buttons

- Primary: warm amber fill, near-black label, slightly stronger hover
- Secondary: white/subtle surface, neutral border, muted disabled state
- Tertiary: text-like actions only for low-risk utilities such as log refresh
- Disabled: low contrast but readable; no warm color
- Loading: keep Streamlit native progress/status behavior
- Icon usage: only when the action benefits from a familiar symbol

### Cards

- Default: avoid extra cards around native form groups
- Proof/data: not used unless real job stats exist
- Product/status: use info/success/warning/error panels with semantic colors
- CTA: primary button only; no decorative CTA card
- Media: not applicable
- Empty/loading: quiet text, no oversized illustration

### Tables / Lists

- Header: compact, high contrast
- Row rhythm: stable height, clear dividers
- Density: operational, not marketing-spacious
- Status cells: semantic text plus color if needed
- Mobile collapse: stack label/value pairs
- Empty/loading: honest state copy only

### Forms

- Label: medium weight, ink text
- Input: cool-gray subtle surface, 10px radius, clear focus ring
- Error/help: semantic panels; no invented remediation claims
- Submit: single primary button
- Success state: Streamlit success panel with brand-compatible green
- Field grouping: expanders for advanced controls; no nested panels

### Badges / Status

- Neutral: soft blue-gray
- Active: accent soft plus brand primary text/border
- Success: soft green
- Warning: soft amber
- Error: soft red
- Size and placement: inline, compact, only when state exists

## Page Patterns

- Hero: compact wordmark and caption, no marketing hero image
- First viewport must show: wordmark, input section, output section, and primary run action on desktop
- Proof section: not applicable unless real generation history is added
- Product/offer section: app controls are the offer
- Case/progress section: runtime logs and task status only
- FAQ/compliance section: not applicable
- Final CTA: no duplicate CTA; keep one primary action
- Footer: not needed for local app
- Mobile-specific changes: reduce padding, keep controls full-width, prevent overflow in upload and button rows

## Motion

- Page reveal: none
- Hover: subtle border/background changes only
- Focus: visible warm focus ring
- Loading: native Streamlit states
- Reduced motion: no custom animation required
- Avoid: pulsing gradients, decorative transitions, loading spinners without state meaning

## Copy Rules

- Voice: direct, operational, Chinese-first where controls are already Chinese
- Claim boundaries: only describe supported providers, files, and outputs that exist in code
- CTA verbs: action-oriented and specific
- Placeholder rules: API keys and paths stay as user-owned input, not examples with fake secrets
- Forbidden language: invented quality claims, customer logos, metrics, public-service promises

## Anti-Patterns

- Do not use Streamlit default red as the primary brand state.
- Do not introduce purple/blue gradient hero treatments.
- Do not wrap every section in a floating card.
- Do not add invented product screenshots, testimonials, or performance claims.
- Do not make advanced controls visually compete with the primary job flow.
- Do not use low-contrast beige text on warm surfaces.

## Implementation Checklist

- Shared tokens are defined before one-off page styling.
- Repeated components use the same geometry, type scale, and state rules.
- Desktop and mobile screenshots show no clipped text, overlap, or horizontal overflow.
- CTAs have clear hierarchy and do not compete.
- Every metric, customer, partner, quote, or proof point is supplied or marked as placeholder.
- Private names, internal numbers, credentials, and unreleased details are not included in reusable docs.
