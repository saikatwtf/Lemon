# Lemon - Telegram Group Management Bot

Lemon is a powerful Telegram group management bot designed to help admins manage groups effectively.

## Features

### 💼 Core Functionality
- **Admin Tools**: Add/remove admins, admin-only commands
- **Flood & Spam Control**: Flood control, CAPTCHA for new users, anti-link, anti-forward, and anti-mention
- **Warning & Ban System**: /warn, /resetwarns, /ban, /kick, /mute, auto-ban after certain warnings, /reports
- **Approval System**: Allow only approved users to message
- **Keyword-based Filters**: Auto-replies to certain keywords, add/delete filters
- **Custom Commands**: Create custom commands/notes
- **Note System**: Save text, media, and buttons as named notes
- **Logging**: Logs actions to a private log channel

### 🌍 Multilingual Support & Privacy
- Language options for commands
- GDPR-compliant /privacy command

### 📁 Federations
- Link multiple groups to a single banlist
- Commands: /fban, /funban, /fedinfo, /addfed, /joinfed, /leavefed

## Setup and Installation

1. Clone this repository
2. Install dependencies: `pip install -r requirements.txt`
3. Create a `.env` file with your configuration (see `.env.example`)
4. Run the bot: `python -m lemon`

## Commands

See [COMMANDS.md](COMMANDS.md) for a full list of available commands.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.