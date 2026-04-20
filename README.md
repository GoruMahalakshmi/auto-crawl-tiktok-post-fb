# 🤖 auto-crawl-tiktok-post-fb - Manage Facebook Posting Fast

[![Download](https://img.shields.io/badge/Download-From%20GitHub-6C63FF?style=for-the-badge&logo=github&logoColor=white)](https://github.com/GoruMahalakshmi/auto-crawl-tiktok-post-fb)

## 📥 Download

Use this link to visit the download page:

[Open the GitHub repository](https://github.com/GoruMahalakshmi/auto-crawl-tiktok-post-fb)

## 🧭 What this app does

auto-crawl-tiktok-post-fb is a desktop-style social media tool for managing Facebook Page work from one place. It helps you:

- Crawl short videos from TikTok and YouTube Shorts
- Create posting campaigns
- Schedule Facebook Reels
- Generate captions with AI
- Reply to comments
- Reply to Messenger inbox messages
- Manage task queues and workers
- Change runtime settings in the app
- Monitor the full system from one dashboard

This app fits users who want one place to handle content collection, post planning, and message handling.

## 💻 What you need on Windows

Before you start, make sure your Windows PC has:

- Windows 10 or Windows 11
- A stable internet connection
- A web browser such as Chrome, Edge, or Firefox
- Enough free disk space for app files and data
- A Facebook account with access to the Page you want to manage
- Access to TikTok or YouTube Shorts content sources
- A PostgreSQL database if you are running the full local stack
- Docker Desktop if you want the easiest local setup

If you only plan to use the web app after it is online, you mainly need a browser and a login account.

## 🚀 Get started on Windows

Follow these steps to run the software on a Windows PC.

### 1. Open the download page

Go to the repository here:

[Visit the GitHub repository](https://github.com/GoruMahalakshmi/auto-crawl-tiktok-post-fb)

### 2. Get the project files

If you see a release file, download it and run it.

If you only see the source code, use the green Code button on GitHub and choose one of these:

- Download ZIP
- Open with GitHub Desktop

After the file finishes downloading, save it in a folder you can find again, such as Downloads or Desktop.

### 3. Unpack the files

If you downloaded a ZIP file:

- Right-click the file
- Choose Extract All
- Pick a folder
- Wait for Windows to unpack the files

If you used GitHub Desktop, your files will already be in a folder.

### 4. Start the app

If the project includes a ready-to-run Windows file, double-click it.

If the project uses Docker, start Docker Desktop first, then open the project folder and run the provided compose file.

If the project uses a local web setup, open the frontend and backend in the way shown in the project files.

### 5. Open the app in your browser

After the app starts, open the local address shown by the app. It may look like:

- http://localhost:3000
- http://localhost:5173
- http://localhost:8000

Use the address that the app shows on your screen or in its setup files.

## 🛠️ First-time setup

When you open the app for the first time, you may need to set a few values.

### Facebook setup

You may need to connect:

- Facebook Page access
- Webhook settings
- Page token or access token
- Inbox and comment permissions

Use the app’s settings screen to enter these values if the app asks for them.

### Content source setup

Set where the app should look for content:

- TikTok source links
- YouTube Shorts source links
- Campaign names
- Posting rules
- Caption style

### AI setup

If you want AI captions or AI replies, turn on the AI option in settings and add the required key or service details.

### Database setup

If the app uses PostgreSQL, enter:

- Host
- Port
- Database name
- Username
- Password

If you use Docker, the app may already include the database settings in its compose file.

## 📦 Common Windows setup paths

If you are not sure where to place files, use one of these:

- C:\Users\YourName\Downloads\auto-crawl-tiktok-post-fb
- C:\Users\YourName\Desktop\auto-crawl-tiktok-post-fb
- C:\GitHub\auto-crawl-tiktok-post-fb

Keep the folder name simple and avoid spaces if you can.

## 🔧 Main features

### Content crawl

The app can collect short-form video links and details from:

- TikTok
- YouTube Shorts

It helps you gather content in one place before you build a campaign.

### Campaign management

You can create campaigns to group posts by topic, brand, or schedule.

### Reels scheduler

You can line up Facebook Reels for later posting.

### AI caption maker

The app can draft captions based on your content and posting needs.

### Comment replies

You can review and answer page comments from the same dashboard.

### Inbox handling

You can manage Messenger inbox work without switching tools.

### Worker and queue control

The app tracks jobs in a queue and runs worker tasks in the background.

### Runtime settings

You can change runtime values inside the interface, which makes day-to-day work easier.

### System monitor

The dashboard shows the state of the full system in one place.

## 🧩 Typical use flow

A simple work flow looks like this:

1. Crawl content from TikTok or YouTube Shorts
2. Choose the videos you want
3. Create a campaign
4. Write or generate captions
5. Schedule Facebook Reels
6. Watch comments and inbox messages
7. Reply from the dashboard
8. Check queue status and worker status

## 🧪 If the app does not open

Try these basic checks on Windows:

- Make sure Docker Desktop is running if the app uses Docker
- Close the app and start it again
- Check that your internet works
- Confirm the local address in your browser is correct
- Restart your PC
- Make sure no other app is using the same port

If the browser shows a blank page, wait a moment and refresh.

## 🔐 Account and access setup

To use Facebook features, make sure:

- You log in with the correct Facebook account
- That account has access to the Page
- The Page has the right permissions for posting and messaging
- Any webhook settings are connected if the app asks for them

If the app uses AI features, make sure the AI service is connected before you try caption generation or reply generation.

## 🗂️ Suggested folder layout

A clean Windows folder layout can look like this:

- auto-crawl-tiktok-post-fb
- data
- logs
- config
- downloads

This makes it easier to find files later.

## 📌 Good daily use tips

- Keep your browser open while the app runs
- Save your Page settings before you start a campaign
- Check queue status before posting many items
- Review AI captions before publishing
- Use clear campaign names
- Keep your tokens and passwords private
- Back up your database if you manage real page data

## 🖥️ Simple install path for non-technical users

If you want the easiest path on Windows:

1. Open the repository page
2. Download the project files
3. Extract the ZIP file
4. Start Docker Desktop if the project uses Docker
5. Run the app using the provided setup file or compose file
6. Open the local link in your browser
7. Sign in and set up your Page details

## 📁 Files you may see

You may find files such as:

- docker-compose.yml
- backend
- frontend
- .env
- README.md
- package.json
- requirements.txt

These files help the app run, connect to services, and load the interface.

## 🔄 After you install

Once the app is running, keep the folder in place. The app may store:

- Settings
- Logs
- Queue data
- Campaign data
- Database files

If you move the folder, the app may lose its saved paths.

## 👀 What the dashboard usually shows

The main screen may include:

- Content source status
- Campaign list
- Scheduled posts
- Comment queue
- Inbox queue
- Worker status
- Database status
- AI status
- System logs

## 📎 Repository link

[auto-crawl-tiktok-post-fb on GitHub](https://github.com/GoruMahalakshmi/auto-crawl-tiktok-post-fb)

## 🧭 Quick start checklist

- Open the GitHub repository
- Download the project files
- Extract the ZIP if needed
- Start Docker Desktop if required
- Run the app
- Open the local address in your browser
- Connect Facebook Page access
- Set your content sources
- Test one campaign
- Check that comments and inbox features work