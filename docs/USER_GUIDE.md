# User Guide

This guide walks through creating a complete product listing from scratch using
Listing Helper. No technical knowledge required.

---

## Getting Started

1. Open your browser and go to **http://localhost:8000**
2. You will see the Dashboard — a board showing all your products grouped by their
   progress stage.

If the page doesn't load, ask your technical contact to start the server
(`python main.py` in the listing_helper folder).

---

## Step 1: Create a New Product

Click **"New Product"** (the blue button at the top of the dashboard).

The Product Wizard opens. You are on Step 1: **Product Info**.

### Option A: Upload a Product Photo (Recommended)

1. Drag and drop a product photo onto the upload zone, or click "Choose File".
2. The app analyzes the photo using AI and auto-fills the form fields (product name,
   category, material, etc.).
3. Review the filled fields and correct anything the AI got wrong.

**Best practices for photos**:
- Use a clear photo on a white or plain background.
- Make sure the product fills most of the frame.
- JPEG or PNG format, under 10 MB.

### Option B: Fill in the Form Manually

Fill in the product details:

| Field | Description | Example |
|---|---|---|
| **Product Name** | What this product is | `Adjustable Cotton Baseball Cap` |
| **SKU** | Your internal code | `CAP-BLK-001` |
| **Brand** | Your brand name | `SportsBrand` |
| **Category** | Product type | `Baseball Caps` |
| **Cost Price (₹)** | Your cost to produce/buy | `150` |
| **Weight (grams)** | Weight for shipping calculation | `120` |
| **HSN Code** | Indian tax code | `65050090` |
| **Notes** | Special instructions for the AI | `Made in India. Focus on durability.` |

### Adding Variations (optional)

If your product comes in different colors or sizes, click **"Add Variation"** for each variant.

| Field | Example |
|---|---|
| Variation Type | `Color` |
| Variation Value | `Black` |
| SKU | `CAP-BLK-001` |

Add one row per variant. The app will generate separate marketplace listings for each.

When finished, click **"Next →"**.

---

## Step 2: Keyword Research

This step finds the words that customers use when searching for your product on Amazon.
Better keywords = more customers finding your listing.

1. The seed keyword (from your product name) is pre-filled. You can change it.
2. You can also paste an Amazon bestseller page URL instead of a keyword.
3. Click **"Start Research"**.

A progress bar shows the research running. This takes 1–3 minutes. The app is reading
real Amazon product pages to find the most-used keywords.

When complete, you will see:
- **Primary Keywords** (pills/badges) — the most important search terms
- **Secondary Keywords** — longer phrases
- **Long-tail Keywords** — very specific phrases

**Select the keywords** you want to use by clicking them (green = selected, grey = not selected).
Pre-select the ones that best describe your product. Aim to keep 10–20 keywords selected.

Click **"Next →"**.

---

## Step 3: AI Content Generation

The app writes your Amazon, Flipkart, and Meesho listing content using the keywords you selected.

1. Click **"Generate AI Copies"**.
2. Wait 10–30 seconds. The AI writes:
   - Amazon: Title, 5 bullet points, description, search terms
   - Flipkart: Title, 10 key features, description, keywords
   - Meesho: Title and description

Three columns appear — one per marketplace. Review each tab.

### Editing Content

Click on any text field to edit it directly. Character counters show you how many
characters you have used vs. the limit:
- **Green counter** = within limit ✓
- **Red counter** = over limit — shorten this field

### If you have variations

Tabs at the top show each variant (Black, Red, etc.). Each variant has its own version
of the content with the color name adapted.

When you are happy with the content, click **"Next →"**.

---

## Step 4: Pricing

The app calculates the right selling price for each marketplace to achieve your target profit margin.

The fee breakdown shows exactly what each marketplace charges:
- Referral/commission fee
- Closing/fixed fee
- Shipping fee
- GST on fees

**To change the target margin**: Use the slider. The prices update automatically.

Review the three price cards and make sure the selling prices seem reasonable for your market.

Click **"Next →"**.

---

## Step 5: Export

This is the final step. You can preview the complete listing data before downloading.

1. Use the marketplace tabs (All / Amazon / Flipkart / Meesho) to review the columns
   that will go into the Excel file.

2. **After you publish** your listings on the marketplace websites, check the
   **"Mark as Listed"** boxes for each marketplace you've published to. This moves
   the product to the "Listed" column on the dashboard.

3. Click **"Download & Finish"**.

The Excel file downloads to your computer. It contains 4 sheets:
- **All Products** — everything in one place
- **Amazon** — ready to import into Amazon Seller Central
- **Flipkart** — ready for Flipkart Seller Hub
- **Meesho** — ready for Meesho Supplier Hub

---

## The Dashboard

After finishing the wizard, you return to the Dashboard.

The **Kanban board** shows your products in 6 columns based on their progress:

| Column | Meaning |
|---|---|
| **New** | Just created, no keywords or content yet |
| **Keywords Done** | Keyword research completed |
| **Content Ready** | AI content generated |
| **Priced** | Selling prices calculated |
| **Exported** | Excel file downloaded |
| **Listed** | Confirmed as live on marketplace(s) |

You can **drag a product card** between columns to manually update its status.

Click on any product card to open it in the wizard and continue from where you left off.

---

## Settings

Click **Settings** in the top navigation bar.

### Gemini API Key
Paste your Google Gemini API key here. Click "Test Key" to confirm it works.
Without a valid key, AI content generation and image detection will not work.

### Scraper Settings
- **Min Delay / Max Delay**: Time (in seconds) to wait between Amazon page requests.
  Increase these if you get blocked frequently. Recommended: 2–5 seconds.
- **Headless Browser**: Keep this ON unless you are debugging.

### Pricing Defaults
- **Default Target Margin**: The starting margin percentage for pricing calculations.
  You can override this per product in the wizard.

---

## Tips

- **Use the image upload** whenever possible. It saves form-filling time and the AI
  often detects product details you might forget to enter.

- **Review AI content carefully**. The AI follows marketplace rules well but may
  occasionally add inaccurate claims about your product. Always verify facts.

- **Add specific notes** in the Product Notes field to guide the AI. For example:
  "This cap is made in India and has a 1-year warranty."

- **Run keyword research from an Amazon bestseller URL** for the most relevant results.
  Go to Amazon, find the bestseller page for your category, copy the URL, and paste
  it in Step 2.

- **Don't rush the research step**. The app needs time to read Amazon pages without
  getting blocked. If you see only generic keywords, try again later with a different
  seed keyword.
