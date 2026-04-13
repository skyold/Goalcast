---
name: mcp-tools
description: Discover and call remote tools (Google Workspace, Notion, Square POS, Odoo, Exa, Apify, Jungle Scout, Lark/Feishu, Twitter, LinkedIn, TikTok, Reddit, GitHub, etc.) via the accio-mcp-cli command-line tool
always_apply: true
---

# mcp-tools

All remote service integrations are invoked with **`accio-mcp-cli`** from the terminal (via bash).
**Recommended workflow:** `toolkit` (browse Phoenix toolkits) → `search` (find tools; alias: `keyword`) → `call`. Do **not** use `list` (it floods context). See the **accio-mcp-cli** skill for flags, auth notes, and troubleshooting.

---

## Architecture

```
Agent (LLM)
  │  bash: accio-mcp-cli toolkit [name]     # optional: Phoenix toolkit overview or tools under a service
  │  bash: accio-mcp-cli search <kw>        # discover tools (alias: keyword)
  │  bash: accio-mcp-cli call <tool-name> [--flags | --json '{...}']
  ▼
accio-mcp-cli → Gateway (default port 4097)
  │  toolkit → browse Phoenix toolkit structure
  │  search (alias: keyword) → full-text search across all tools
  │  call (alias: run) → invoke tool by name
  ▼
MCP servers (Phoenix, Composio, custom MCP)
```

Key points:
- `user_google_email` is **required** for all Google tools — pass it as a CLI flag (e.g. `--user_google_email`) or inside `--json` with other arguments.
- Prefer **`search`** before **`call`** — confirms exact tool names and parameters. Use **`toolkit`** when you need Phoenix toolkit structure.
- Timeout: 60 s per tool (accio-mcp-cli); use `--raw` for full JSON when debugging.

---

## Quick Reference

| Command | Purpose | Notes |
|---------|---------|-------|
| `accio-mcp-cli search <keyword>` | Full-text search across all tools (Phoenix + Composio + custom) | Alias: `keyword`; use first when unsure of tool name |
| `accio-mcp-cli toolkit [keyword]` | Browse Phoenix toolkit structure or list tools under a toolkit/service | No keyword → overview; with keyword → tools under match |
| `accio-mcp-cli call <tool-name> ...` | Execute a tool | Alias: `run`; nested args → `--json '{...}'` |

---

## Available Toolkits

### Google Workspace (~92 tools)

#### Auth (1)

| Tool | Description |
|------|-------------|
| `start_google_auth` | Initiate Google OAuth flow. Optional params: `service_name` (default "Gmail") |

#### Gmail (19)

| Tool | Description | Key Params |
|------|-------------|------------|
| `search_gmail_messages` | Search Gmail messages | `query`, `page_size`(10), `page_token` |
| `get_gmail_message_content` | Get single message content | `message_id` |
| `get_gmail_messages_content_batch` | Get multiple messages at once | `message_ids` (List), `format`("full") |
| `get_gmail_attachment_content` | Get attachment (uploads to CDN) | `message_id`, `attachment_id` |
| `send_gmail_message` | Send email | `to`, `subject`, `body`, `body_format`("plain"), `cc`, `bcc`, `thread_id` |
| `draft_gmail_message` | Create draft | `to`, `subject`, `body`, `body_format`, `cc`, `bcc` |
| `get_gmail_thread_content` | Get full thread | `thread_id` |
| `get_gmail_threads_content_batch` | Get multiple threads at once | `thread_ids` (List) |
| `list_gmail_labels` | List all labels | — |
| `manage_gmail_label` | Create/update/delete a label | `action`("create"\|"update"\|"delete"), `label_name`, `label_id`, `new_name` |
| `modify_gmail_message_labels` | Add/remove labels on a message | `message_id`, `add_label_ids`, `remove_label_ids` |
| `batch_modify_gmail_message_labels` | Batch modify labels on messages | `message_ids`, `add_label_ids`, `remove_label_ids` |
| `list_gmail_filters` | List all filters | — |
| `create_gmail_filter` | Create filter rule | `criteria` (dict), `action` (dict) |
| `delete_gmail_filter` | Delete filter | `filter_id` |
| `setup_gmail_watch` | Set up Gmail push notifications via Pub/Sub | `pubsub_topic_name`, `label_ids`, `filter_query` |
| `stop_gmail_watch` | Stop Gmail watch and clear config | — |
| `get_gmail_watch_status` | Get current watch config and expiration | — |
| `renew_gmail_watch` | Renew watch (extends ~7 days) | — |

#### Calendar (5)

| Tool | Description | Key Params |
|------|-------------|------------|
| `list_calendars` | List all calendars | — |
| `get_events` | Get calendar events | `calendar_id`("primary"), `event_id`, `time_min`, `time_max`, `query`, `max_results`(25), `detailed`, `include_attachments` |
| `create_calendar_event` | Create event | `summary`, `start_time`, `end_time`, `description`, `location`, `attendees`, `timezone`, `attachments`, `add_google_meet`, `reminders` |
| `modify_calendar_event` | Update event | `event_id`, `summary`, `start_time`, `end_time`, `description`, `location`, `attendees`, etc. |
| `delete_calendar_event` | Delete event | `event_id`, `calendar_id` |

#### Tasks (12)

| Tool | Description | Key Params |
|------|-------------|------------|
| `list_task_lists` | List all task lists | `max_results`(1000), `page_token` |
| `get_task_list` | Get specific task list | `task_list_id` |
| `create_task_list` | Create task list | `title` |
| `update_task_list` | Rename task list | `task_list_id`, `title` |
| `delete_task_list` | Delete task list | `task_list_id` |
| `list_tasks` | List tasks in a list | `task_list_id`("@default"), `max_results`(100), `show_completed`(false), `page_token` |
| `get_task` | Get specific task | `task_list_id`, `task_id` |
| `create_task` | Create task | `title`, `task_list_id`("@default"), `notes`, `due` |
| `update_task` | Update task | `task_list_id`, `task_id`, `title`, `notes`, `due`, `status` |
| `delete_task` | Delete task | `task_list_id`, `task_id` |
| `move_task` | Reorder/reparent task | `task_list_id`, `task_id`, `parent`, `previous` |
| `clear_completed_tasks` | Clear completed in a list | `task_list_id` |

#### Drive (14)

| Tool | Description | Key Params |
|------|-------------|------------|
| `search_drive_files` | Search files | `query`, `page_size`(10), `drive_id`, `corpora` |
| `get_drive_file_content` | Get file content | `file_id` |
| `get_drive_file_download_url` | Get download/export URL | `file_id`, `export_format` |
| `list_drive_items` | List items in folder | `folder_id`("root"), `page_size`(100), `drive_id`, `corpora` |
| `create_drive_file` | Create/upload file | `file_name`, `content`, `folder_id`("root"), `mime_type`("text/plain"), `fileUrl` |
| `update_drive_file` | Update file metadata | `file_id`, `name`, `description`, `mime_type`, `add_parents`, `remove_parents`, `starred`, `trashed` |
| `get_drive_file_permissions` | Get file permissions | `file_id` |
| `check_drive_file_public_access` | Check public access | `file_name` |
| `get_drive_shareable_link` | Get shareable link | `file_id` |
| `share_drive_file` | Share file | `file_id`, `share_with`, `role`("reader"), `share_type`, `send_notification`, `email_message`, `expiration_time` |
| `batch_share_drive_file` | Batch share with multiple recipients | `file_id`, `recipients` (List[Dict]), `send_notification`, `email_message` |
| `update_drive_permission` | Update permission role | `file_id`, `permission_id`, `role`, `expiration_time` |
| `remove_drive_permission` | Remove permission | `file_id`, `permission_id` |
| `transfer_drive_ownership` | Transfer ownership | `file_id`, `new_owner_email`, `move_to_new_owners_root`(false) |

#### Sheets (10)

| Tool | Description | Key Params |
|------|-------------|------------|
| `list_spreadsheets` | List spreadsheets | `max_results`(25) |
| `get_spreadsheet_info` | Get spreadsheet metadata | `spreadsheet_id` |
| `create_spreadsheet` | Create spreadsheet | `title`, `sheet_names` |
| `create_sheet` | Add sheet tab | `spreadsheet_id`, `sheet_name` |
| `read_sheet_values` | Read cell values | `spreadsheet_id`, `range_name`("A1:Z1000") |
| `modify_sheet_values` | Write/clear cell values | `spreadsheet_id`, `range_name`, `values`, `value_input_option`, `clear_values` |
| `format_sheet_range` | Format cells | `spreadsheet_id`, `range_name`, `background_color`, `text_color`, `number_format_type`, `number_format_pattern` |
| `add_conditional_formatting` | Add conditional format rule | `spreadsheet_id`, `range_name`, `condition_type`, `condition_values`, `background_color`, `text_color`, `gradient_points` |
| `update_conditional_formatting` | Update conditional format rule | `spreadsheet_id`, `rule_index`, `range_name`, `condition_type`, etc. |
| `delete_conditional_formatting` | Delete conditional format rule | `spreadsheet_id`, `rule_index`, `sheet_name` |

#### Docs (14)

| Tool | Description | Key Params |
|------|-------------|------------|
| `search_docs` | Search documents | `query`, `page_size`(10) |
| `get_doc_content` | Get document content | `document_id` |
| `list_docs_in_folder` | List docs in folder | `folder_id`("root"), `page_size`(100) |
| `create_doc` | Create document | `title`, `content`("") |
| `modify_doc_text` | Modify text (format/replace) | `document_id`, `start_index`, `end_index`, `text`, `bold`, `italic`, `underline`, `font_size`, `font_family`, `text_color`, `background_color` |
| `find_and_replace_doc` | Find and replace text | `document_id`, `find_text`, `replace_text`, `match_case`(false) |
| `insert_doc_elements` | Insert table/list/text | `document_id`, `element_type`, `index`, `rows`, `columns`, `list_type`, `text` |
| `insert_doc_image` | Insert image | `document_id`, `image_source`, `index`, `width`, `height` |
| `update_doc_headers_footers` | Update headers/footers | `document_id`, `section_type`, `content`, `header_footer_type` |
| `batch_update_doc` | Batch update operations | `document_id`, `operations` (List[Dict]) |
| `inspect_doc_structure` | Inspect doc element tree | `document_id`, `detailed`(false) |
| `create_table_with_data` | Insert table with data | `document_id`, `table_data`, `index`, `bold_headers`(true) |
| `debug_table_structure` | Debug table elements | `document_id`, `table_index`(0) |
| `export_doc_to_pdf` | Export to PDF | `document_id`, `pdf_filename`, `folder_id` |

#### Slides (5)

| Tool | Description | Key Params |
|------|-------------|------------|
| `create_presentation` | Create presentation | `title`("Untitled Presentation") |
| `get_presentation` | Get presentation details | `presentation_id` |
| `batch_update_presentation` | Batch update slides | `presentation_id`, `requests` (List[Dict]) |
| `get_page` | Get slide page details | `presentation_id`, `page_object_id` |
| `get_page_thumbnail` | Get slide thumbnail URL | `presentation_id`, `page_object_id`, `thumbnail_size`("MEDIUM") |

#### Forms (5)

| Tool | Description | Key Params |
|------|-------------|------------|
| `create_form` | Create form | `title`, `description`, `document_title` |
| `get_form` | Get form details | `form_id` |
| `set_publish_settings` | Set form publish settings | `form_id`, `publish_as_template`(false), `require_authentication`(false) |
| `list_form_responses` | List form responses | `form_id`, `page_size`(10), `page_token` |
| `get_form_response` | Get single response | `form_id`, `response_id` |

#### Chat (4)

| Tool | Description | Key Params |
|------|-------------|------------|
| `list_spaces` | List Chat spaces | `page_size`(100), `space_type`("all") |
| `get_messages` | Get messages from space | `space_id`, `page_size`(50), `order_by`("createTime desc") |
| `send_message` | Send message to space | `space_id`, `message_text`, `thread_key` |
| `search_messages` | Search Chat messages | `query`, `space_id`, `page_size`(25) |

#### Search (3)

| Tool | Description | Key Params |
|------|-------------|------------|
| `search_custom` | Google Custom Search | `q`, `num`(10), `start`(1), `date_restrict`, `exact_terms`, `exclude_terms`, `file_type`, `gl`, `hl`, `site_search`, `sort` |
| `search_custom_siterestrict` | Site-restricted search | `q`, `sites` (List[str]), `num`(10), `start`(1) |
| `get_search_engine_info` | Get search engine metadata | — |

---

### Notion (24 tools)

#### Auth (5)

| Tool | Description | Key Params |
|------|-------------|------------|
| `start_notion_auth` | Start Notion OAuth 2.0 flow | — |
| `set_notion_token` | Set Notion integration token | `token` |
| `check_notion_token` | Check token validity | — |
| `delete_notion_token` | Delete stored token | — |
| `list_notion_token_users` | List users with tokens | — |

#### Search (1)

| Tool | Description | Key Params |
|------|-------------|------------|
| `search_notion` | Search workspace | `query`, `filter_type`("page"\|"database"), `page_size`(100) |

#### Pages (5)

| Tool | Description | Key Params |
|------|-------------|------------|
| `get_notion_page` | Get page by ID | `page_id` |
| `create_notion_page` | Create page | `parent` (dict), `properties` (dict), `children` (list) |
| `update_notion_page_properties` | Update page properties | `page_id`, `properties` |
| `archive_notion_page` | Archive (soft delete) page | `page_id` |
| `restore_notion_page` | Restore archived page | `page_id` |

#### Databases (4)

| Tool | Description | Key Params |
|------|-------------|------------|
| `get_notion_database` | Get database by ID | `database_id` |
| `query_notion_database` | Query with filters/sorts | `database_id`, `filter_obj`, `sorts`, `page_size`(100) |
| `create_notion_database` | Create database | `parent`, `title`, `properties` |
| `update_notion_database` | Update database | `database_id`, `title`, `properties` |

#### Blocks (5)

| Tool | Description | Key Params |
|------|-------------|------------|
| `get_notion_block` | Get block by ID | `block_id` |
| `get_notion_block_children` | Get child blocks | `block_id`, `page_size`(100) |
| `append_notion_block_children` | Append children | `block_id`, `children` (List[Dict]) |
| `update_notion_block` | Update block | `block_id`, `block_data` (dict) |
| `delete_notion_block` | Delete (archive) block | `block_id` |

#### Comments (2)

| Tool | Description | Key Params |
|------|-------------|------------|
| `get_notion_comments` | Get comments | `block_id`, `page_size`(100) |
| `create_notion_comment` | Create comment | `parent` (dict), `rich_text` (List[Dict]) |

#### Users (3)

| Tool | Description | Key Params |
|------|-------------|------------|
| `get_notion_user` | Get user by ID | `notion_user_id` |
| `list_notion_users` | List workspace users | `page_size`(100) |
| `get_notion_bot_user` | Get bot user info | — |

---

### Square POS (21 tools)

#### Auth (1)

| Tool | Description | Key Params |
|------|-------------|------------|
| `start_square_auth` | Start Square OAuth flow | `merchant_label` |

#### Locations (2)

| Tool | Description | Key Params |
|------|-------------|------------|
| `list_square_locations` | List merchant locations | `merchant_id` |
| `get_square_location` | Get location by ID | `merchant_id`, `location_id` |

#### Payments (2)

| Tool | Description | Key Params |
|------|-------------|------------|
| `list_square_payments` | List transactions | `merchant_id`, `begin_time`, `end_time`, `location_id`, `limit`(50), `sort_order`("DESC"), `cursor` |
| `get_square_payment` | Get payment by ID | `merchant_id`, `payment_id` |

#### Orders (3)

| Tool | Description | Key Params |
|------|-------------|------------|
| `search_square_orders` | Search orders | `merchant_id`, `location_ids`, `query` (JSON), `limit`(50), `cursor` |
| `get_square_order` | Get order by ID | `merchant_id`, `order_id` |
| `create_square_order` | Create order | `merchant_id`, `location_id`, `idempotency_key`, `line_items` (JSON) |

#### Customers (4)

| Tool | Description | Key Params |
|------|-------------|------------|
| `list_square_customers` | List customers | `merchant_id`, `limit`(50), `sort_field`, `sort_order`, `cursor` |
| `get_square_customer` | Get customer by ID | `merchant_id`, `customer_id` |
| `search_square_customers` | Search customers | `merchant_id`, `query` (JSON), `limit`, `cursor` |
| `create_square_customer` | Create customer | `merchant_id`, `idempotency_key`, `given_name`, `family_name`, `email_address`, `phone_number`, `company_name`, `note` |

#### Catalog (4)

| Tool | Description | Key Params |
|------|-------------|------------|
| `list_square_catalog` | List catalog objects | `merchant_id`, `types`("ITEM"), `cursor` |
| `get_square_catalog_object` | Get catalog object | `merchant_id`, `object_id`, `include_related_objects`(false) |
| `search_square_catalog` | Search catalog by text | `merchant_id`, `text_query`, `object_types`("ITEM"), `limit`(100), `cursor` |
| `upsert_square_catalog_object` | Create/update catalog object | `merchant_id`, `idempotency_key`, `object_type`, `object_id`, `object_data` (JSON) |

#### Inventory (5)

| Tool | Description | Key Params |
|------|-------------|------------|
| `get_square_inventory_count` | Get inventory count | `merchant_id`, `catalog_object_id`, `location_ids` |
| `batch_retrieve_square_inventory` | Batch retrieve counts | `merchant_id`, `catalog_object_ids`, `location_ids` |
| `adjust_square_inventory` | Adjust inventory quantity | `merchant_id`, `catalog_object_id`, `location_id`, `quantity`, `from_state`("NONE"), `to_state`("IN_STOCK") |
| `set_square_inventory_physical_count` | Set physical count (stocktake) | `merchant_id`, `catalog_object_id`, `location_id`, `quantity`, `state`("IN_STOCK") |
| `transfer_square_inventory` | Transfer between locations | `merchant_id`, `catalog_object_id`, `from_location_id`, `to_location_id`, `quantity` |

---

### Odoo ERP / WMS (7 tools)

#### ERP (4)

| Tool | Description | Key Params |
|------|-------------|------------|
| `odoo_configure` | Configure Odoo connection | `url`, `db`, `user`, `password` |
| `odoo_query_purchase_order` | Query PO by number | `po_number` |
| `odoo_list_purchase_orders` | List POs | `vendor`, `status`, `limit`(20) |
| `odoo_query_vendor` | Query vendor info | `vendor_name`, `vendor_id` |

#### WMS (3)

| Tool | Description | Key Params |
|------|-------------|------------|
| `odoo_query_goods_receipt_by_po` | Query receipts by PO | `po_number` |
| `odoo_query_goods_receipt` | Query receipt by number | `gr_number` |
| `odoo_list_goods_receipts` | List goods receipts | `date_from`, `date_to`, `state`, `limit`(20) |

---

### Exa Search (8 tools)

Native tools (4):

| Tool | Description | Key Params |
|------|-------------|------------|
| `web_search_exa` | Semantic web search | `query`, `num_results`(10), `include_domains`, `exclude_domains`, `start_published_date`, `end_published_date`, `include_text`, `type`("auto") |
| `find_similar_pages_exa` | Find similar pages to URL | `url`, `num_results`(10), `exclude_source_domain`(true) |
| `get_page_contents_exa` | Extract content from URLs | `urls` (List[str]), `text`(true), `summary`(false) |
| `exa_answer` | Direct answer with citations | `query`, `text`(true) |

Proxy tools (4, prefixed `exa_`):

| Tool | Description |
|------|-------------|
| `exa_web_search_exa` | Proxy: Exa web search via mcp.exa.ai |
| `exa_company_research_exa` | Proxy: Company research |
| `exa_people_search_exa` | Proxy: People search |
| `exa_get_code_context_exa` | Proxy: Code context search |

---

### Apify (proxy tools, prefixed `apify_`)

Apify tools are proxied from the remote Apify MCP server (`mcp.apify.com`). The
MCP server handles authentication (via `APIFY_TOKEN` env var) so the token is never
exposed to the agent. All tools are mounted under the `apify_` namespace prefix.

Apify provides thousands of ready-made "Actors" for web scraping, data extraction,
and automation. The key proxy tools include:

| Tool | Description |
|------|-------------|
| `apify_search-actors` | Search for Actors in the Apify Store by keyword |
| `apify_get-actor-details` | Get details & README for a specific Actor |
| `apify_call-actor` | Run an Actor with given input and wait for results |
| `apify_get-dataset-items` | Retrieve items from a dataset (Actor run output) |
| `apify_rag-web-browser` | RAG-optimized web browser — fetches and extracts a URL |
| `apify_get-user-info` | Get the authenticated Apify user profile |

> **Note:** Available tools depend on the remote Apify MCP server. Use
> `accio-mcp-cli search apify` to discover all currently available tools.

Common use cases:
- Scrape social media (Instagram, TikTok, Facebook, YouTube, etc.)
- Extract data from e-commerce sites (Amazon, Shopee, etc.)
- Crawl and extract content from any website
- RAG-optimized browsing for AI pipelines

---

### Jungle Scout (6 tools)

Amazon product research tools powered by the Jungle Scout API. Authorization
(`JS_KEY_NAME` / `JS_API_KEY`) is kept server-side — only business parameters
are exposed to the agent.

| Tool | Description | Key Params |
|------|-------------|------------|
| `js_product_database_query` | Search Amazon product database | `marketplace`("us"), `include_keywords`, `exclude_keywords`, `categories`, `min_price`, `max_price`, `min_revenue`, `max_revenue`, `page_size`(50) |
| `js_historical_search_volume` | Get historical search volume trend | `keyword`, `start_date`, `end_date`, `marketplace`("us") |
| `js_sales_estimates` | Get estimated sales for an ASIN | `asin`, `start_date`, `end_date`, `marketplace`("us") |
| `js_share_of_voice` | Get share of voice for a keyword | `keyword`, `marketplace`("us") |
| `js_keywords_by_asin` | Find keywords ASINs rank for | `asins` (List[str]), `marketplace`("us"), `include_variants`(true), `page_size`(50) |
| `js_keywords_by_keyword` | Find related keywords | `search_terms`, `marketplace`("us"), `categories`, `page_size`(50) |

Supported marketplaces: `us`, `uk`, `ca`, `de`, `fr`, `it`, `es`, `mx`, `jp`, `in`.

---

### Twitter / X (24 tools)

#### Auth (1)

| Tool | Description |
|------|-------------|
| `start_twitter_auth` | Start Twitter/X OAuth 2.0 flow |

#### Tweets (10)

| Tool | Description | Key Params |
|------|-------------|------------|
| `post_tweet` | Post tweet with optional images | `text`, `media_urls` (List of image URLs or file paths, max 4), `reply_to`, `tags` |
| `delete_tweet` | Delete tweet | `tweet_id` |
| `get_tweet_details` | Get tweet details | `tweet_id` |
| `create_poll_tweet` | Create poll | `text`, `choices` (List), `duration_minutes` |
| `vote_on_poll` | Vote on poll | `tweet_id`, `choice` |
| `favorite_tweet` | Like tweet | `tweet_id` |
| `unfavorite_tweet` | Unlike tweet | `tweet_id` |
| `bookmark_tweet` | Bookmark tweet | `tweet_id`, `folder_id` |
| `delete_bookmark` | Remove bookmark | `tweet_id` |
| `delete_all_bookmarks` | Clear all bookmarks | — |

#### Timeline & Search (5)

| Tool | Description | Key Params |
|------|-------------|------------|
| `get_timeline` | Home timeline (For You) | `count`(100), `seen_tweet_ids`, `cursor` |
| `get_latest_timeline` | Home timeline (Following) | `count`(100) |
| `search_twitter` | Search tweets | `query`, `product`("Top"), `count`, `cursor` |
| `get_trends` | Get trending topics | `category`, `count` |
| `get_highlights_tweets` | Get highlighted tweets | `user_id`, `count`, `cursor` |

#### Users (8)

| Tool | Description | Key Params |
|------|-------------|------------|
| `get_user_profile` | Get user profile | `user_id` |
| `get_user_by_screen_name` | Get user by @ handle | `screen_name` |
| `get_user_by_id` | Get user by ID | `user_id` |
| `get_user_followers` | Get user followers | `user_id`, `count`(100), `cursor` |
| `get_user_following` | Get following list | `user_id`, `count`, `cursor` |
| `get_user_followers_you_know` | Get mutual followers | `user_id`, `count`, `cursor` |
| `get_user_subscriptions` | Get subscriptions | `user_id`, `count`, `cursor` |
| `get_user_mentions` | Get mentions of user | `user_id`, `count`, `cursor` |

---

### LinkedIn (8 tools)

#### Auth (1)

| Tool | Description |
|------|-------------|
| `start_linkedin_auth` | Start LinkedIn OAuth flow |

#### Tools (7)

| Tool | Description | Key Params |
|------|-------------|------------|
| `linkedin_get_person_profile` | Get person profile | `linkedin_username`, `sections` |
| `linkedin_search_people` | Search people | `keywords`, `location` |
| `linkedin_get_company_profile` | Get company profile | `company_name`, `sections` |
| `linkedin_get_company_posts` | Get company posts | `company_name` |
| `linkedin_search_jobs` | Search jobs | `keywords`, `location` |
| `linkedin_get_job_details` | Get job details | `job_id` |
| `linkedin_close_session` | Close browser session | — |

---

### TikTok (6 tools)

#### Auth (1)

| Tool | Description |
|------|-------------|
| `start_tiktok_auth` | Start TikTok OAuth flow |

#### Tools (5)

| Tool | Description | Key Params |
|------|-------------|------------|
| `tiktok_search_videos` | Search videos by hashtag | `search_terms` (List[str]), `count`(30) |
| `tiktok_get_trending_videos` | Get trending videos | `count`(30) |
| `tiktok_get_video_detail` | Get video detail by URL | `video_url` |
| `tiktok_get_user_videos` | Get user's videos | `username`, `count`(30) |
| `tiktok_get_user_info` | Get user profile | `username` |

---

### Reddit (7 tools)

| Tool | Description | Key Params |
|------|-------------|------------|
| `get_submission` | Get post by ID | `submission_id` |
| `get_subreddit` | Get subreddit info | `subreddit_name` |
| `get_comment` | Get comment by ID | `comment_id` |
| `get_comments_by_submission` | Get all comments on a post | `submission_id`, `replace_more`(true) |
| `search_posts` | Search posts in subreddit | `subreddit_name`, `query`, `sort`("relevance"), `syntax`("lucene"), `time_filter`("all") |
| `search_subreddits_by_name` | Search subreddits by name | `query`, `include_nsfw`(false), `exact_match`(false) |
| `search_subreddits_by_description` | Search subreddits by description | `query`, `include_full_description`(false) |

---

### GitHub (1 tool)

| Tool | Description |
|------|-------------|
| `start_github_auth` | Start GitHub OAuth flow |

---

### Lark / Feishu (auth only — business ops use local lark-cli, see lark-tools skill)

| Tool | Description |
|------|-------------|
| `start_lark_auth` | Start Lark Device Flow authorization (Connector UI use only) |
| `check_lark_auth` | Check Lark auth status (Connector UI use only) |
| `export_lark_credentials` | Export credentials for syncing to local machine (Connector UI use only) |

> **Do NOT call lark MCP tools for business operations** (messaging, calendar, docs, etc.).
> Use the **lark-tools** skill instead, which runs `lark-cli` commands locally via bash.

---

## How to Use `accio-mcp-cli`

### Step 1 — Discover tools (when unsure of exact name or parameters)

```bash
accio-mcp-cli search gmail
```

This returns matching tool names with their full parameter schemas (alias: `accio-mcp-cli keyword gmail`). Use this when you need to check the exact parameter names before calling a tool. For Phoenix toolkit structure, use `accio-mcp-cli toolkit gmail`.

### Step 2 — Execute a tool

```bash
accio-mcp-cli call search_gmail_messages --user_google_email "user@example.com" \
  --query "from:sales@futuretech.com subject:发票" --page_size 10
```

Use `--json '{...}'` when arguments are nested (objects/arrays). `--json` takes precedence over individual flags.

---

## Complete Examples

### Gmail — Search and read

```bash
accio-mcp-cli call search_gmail_messages --user_google_email "user@example.com" \
  --query "from:sales@futuretech.com has:attachment" --page_size 5
```

Then read message content:

```bash
accio-mcp-cli call get_gmail_message_content --user_google_email "user@example.com" \
  --message_id "<id from search results>"
```

Batch read multiple messages:

```bash
accio-mcp-cli call get_gmail_messages_content_batch --user_google_email "user@example.com" \
  --json '{"message_ids":["<id1>","<id2>","<id3>"]}'
```

### Gmail — Manage labels

```bash
accio-mcp-cli call manage_gmail_label --user_google_email "user@example.com" \
  --json '{"action":"create","label_name":"Invoices/2026"}'
```

### Calendar — Create event with Google Meet

```bash
accio-mcp-cli call create_calendar_event --user_google_email "user@example.com" \
  --json '{"summary":"Weekly Sync","start_time":"2026-03-10T10:00:00","end_time":"2026-03-10T11:00:00","timezone":"Asia/Shanghai","attendees":["alice@company.com","bob@company.com"],"add_google_meet":true}'
```

### Drive — Download file

```bash
accio-mcp-cli call get_drive_file_download_url --user_google_email "user@example.com" \
  --file_id "<file_id>" --export_format pdf
```

### Sheets — Read and write

```bash
accio-mcp-cli call read_sheet_values --user_google_email "user@example.com" \
  --spreadsheet_id "<spreadsheet_id>" --range_name "Sheet1!A1:D50"
```

```bash
accio-mcp-cli call modify_sheet_values --user_google_email "user@example.com" \
  --json '{"spreadsheet_id":"<spreadsheet_id>","range_name":"Sheet1!A1:C3","values":[["Name","Score","Grade"],["Alice",95,"A"],["Bob",87,"B"]]}'
```

### Docs — Create and populate

```bash
accio-mcp-cli call create_doc --user_google_email "user@example.com" \
  --json '{"title":"会议记录 - 2026-03-05","content":"# 参会人员\n- Alice\n- Bob\n\n# 讨论事项\n..."}'
```

### Notion — Query database

```bash
accio-mcp-cli call query_notion_database --json '{"database_id":"<database_id>","filter_obj":{"property":"Status","select":{"equals":"In Progress"}},"sorts":[{"property":"Due Date","direction":"ascending"}]}'
```

### Square — List payments

```bash
accio-mcp-cli call list_square_payments \
  --json '{"merchant_id":"<merchant_id>","begin_time":"2026-03-01T00:00:00Z","end_time":"2026-03-05T23:59:59Z","limit":20}'
```

### Square — Search catalog

```bash
accio-mcp-cli call search_square_catalog \
  --merchant_id "<merchant_id>" --text_query coffee --object_types ITEM
```

### Odoo — Query purchase order

```bash
accio-mcp-cli call odoo_query_purchase_order --po_number "PO-2026-088"
```

### Exa — Web search

```bash
accio-mcp-cli call web_search_exa \
  --json '{"query":"AI agent frameworks 2026","num_results":5,"include_domains":["github.com","arxiv.org"]}'
```

### Exa — Get direct answer

```bash
accio-mcp-cli call exa_answer --json '{"query":"What is the latest version of React?"}'
```

### Apify — Search and run an Actor

```bash
accio-mcp-cli call apify_search-actors --search "instagram scraper"
```

```bash
accio-mcp-cli call apify_call-actor \
  --json '{"actorId":"apify/instagram-scraper","input":{"directUrls":["https://www.instagram.com/natgeo/"],"resultsLimit":10}}'
```

### Jungle Scout — Product research

```bash
accio-mcp-cli call js_product_database_query \
  --json '{"marketplace":"us","include_keywords":["yoga mat"],"categories":["Sports & Outdoors"],"min_revenue":5000}'
```

### Jungle Scout — Keyword research

```bash
accio-mcp-cli call js_keywords_by_asin \
  --json '{"asins":["B00I26U9WS"],"marketplace":"us"}'
```

### Jungle Scout — Historical search volume

```bash
accio-mcp-cli call js_historical_search_volume \
  --json '{"keyword":"portable charger","start_date":"2026-01-01","end_date":"2026-03-01","marketplace":"us"}'
```

### Twitter — Post tweet with images

```bash
accio-mcp-cli call post_tweet \
  --json '{"text":"Check out our new product launch!","media_urls":["https://example.com/product-photo.jpg","https://example.com/product-banner.png"],"tags":["launch","newproduct"]}'
```

### LinkedIn — Search people

```bash
accio-mcp-cli call linkedin_search_people --keywords "AI engineer" --location "San Francisco"
```

### TikTok — Search videos

```bash
accio-mcp-cli call tiktok_search_videos \
  --json '{"search_terms":["AI tutorial","machine learning"],"count":10}'
```

### Reddit — Search posts

```bash
accio-mcp-cli call search_posts \
  --json '{"subreddit_name":"MachineLearning","query":"transformer architecture","sort":"top","time_filter":"month"}'
```

---

## Important Rules

1. **Always use `accio-mcp-cli`** (from bash) — never try to call tool names like `search_gmail_messages`
   as standalone LLM tools. Discover with `search` (alias: `keyword`), then `call`.

2. **NEVER guess tool names** — always run `accio-mcp-cli search <term>` (e.g. `gmail`) to discover
   exact tool names before calling. For example, `list_gmail_messages` does NOT exist — the correct tool is `search_gmail_messages`.

3. **Prefer a specific search term** — `accio-mcp-cli search gmail` returns richer matches than
   vague terms. Use `accio-mcp-cli toolkit` when you need Phoenix toolkit structure.

4. **`user_google_email` is required** — All Google tools require `user_google_email` in the payload.
   Pass `--user_google_email` or include it in `--json`. Get the address from the user or conversation context.

5. **Confirm before destructive operations**:
   - `send_gmail_message` — confirm recipient and content
   - `post_tweet` — confirm tweet content and any media before posting
   - `share_drive_file`, `batch_share_drive_file` — confirm who gets access
   - `delete_*` operations — always confirm
   - `transfer_drive_ownership` — confirm new owner
   - `create_square_order` — confirm order details and amount

6. **Odoo requires configuration first** — if the user hasn't configured Odoo credentials,
   call `odoo_configure` before any other `odoo_*` tool.

7. **Notion requires authentication** — if Notion calls fail with auth errors, guide
   the user to authenticate via `start_notion_auth` or set a token via `set_notion_token`.

8. **Twitter requires authentication** — if Twitter calls fail with auth errors, guide
   the user to authenticate via `start_twitter_auth`.

9. **Square requires authentication** — call `start_square_auth` before using any
   Square tools if not yet authenticated.

10. **LinkedIn session management** — LinkedIn tools may require an active session. Use
    `linkedin_close_session` to properly close sessions when done.

11. **TikTok requires authentication** — call `start_tiktok_auth` if TikTok tools fail.

12. **Apify tools are dynamic** — the available Apify tools depend on the remote
    Apify MCP server. Always use `accio-mcp-cli search apify` to discover
    exact tool names before calling. All Apify tools are prefixed with `apify_`.

13. **Jungle Scout authentication is server-side** — `JS_KEY_NAME` and `JS_API_KEY`
    are managed by the MCP server. The agent does not need to handle credentials.

14. **Lark uses local CLI, not accio-mcp-cli** — do NOT use `accio-mcp-cli` for Lark business operations.
    Use the **lark-tools** skill which runs `lark-cli` locally via bash.
    The MCP lark auth tools (`start_lark_auth` etc.) are for Connector UI only.

15. **Error handling** — if a tool call returns an error, report it clearly to the user.
    Do not retry silently. Common issues:
    - Authentication expired → guide user to re-auth via `start_*_auth`
    - Missing required params → use `accio-mcp-cli search <area>` to check schema
    - Rate limits → wait and retry once
    - Timeout → retry once (60 s typical per accio-mcp-cli)
