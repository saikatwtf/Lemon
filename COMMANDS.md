# Lemon Bot Commands

## General Commands
- `/start` - Start the bot
- `/help` - Get help information
- `/settings` - Configure bot settings for your group
- `/language` - Change bot language
- `/privacy` - View privacy policy

## Greeting Commands
- `/setwelcome` - Set welcome message for new members
- `/setwelcome on/off` - Enable/disable welcome messages
- `/setwelcome captcha on/off` - Enable/disable CAPTCHA verification
- `/setwelcome captcha timeout <seconds>` - Set CAPTCHA timeout
- `/setfarewell` - Set farewell message for members who leave
- `/setfarewell on/off` - Enable/disable farewell messages

## Cleaning Commands
- `/purge` - Delete a range of messages (reply to a message to start from)
- `/del` - Delete a specific message (reply to the message)
- `/clean` - Clean bot messages or specific message types
- `/clean bot [limit]` - Clean bot messages
- `/clean commands [limit]` - Clean command messages
- `/clean all [limit]` - Clean all messages
- `/cleanservice on/off` - Enable/disable automatic removal of service messages
- `/cleanservice pin on/off` - Enable/disable silent pin notifications

## Admin Commands
- `/adminlist` - List all admins in the group
- `/promote` - Promote a user to admin
- `/demote` - Demote an admin to regular user
- `/pin` - Pin a message
- `/unpin` - Unpin a message
- `/unpinall` - Unpin all messages

## Moderation Commands
- `/ban` - Ban a user
- `/unban` - Unban a user
- `/kick` - Kick a user
- `/mute` - Mute a user
- `/unmute` - Unmute a user
- `/warn` - Warn a user
- `/resetwarns` - Reset warnings for a user
- `/warns` - Check warnings for a user
- `/report` - Report a message to admins

## Filter Commands
- `/filter` - Add a new filter
- `/stop` - Remove a filter
- `/filters` - List all filters
- `/cleanfilters` - Remove all filters

## Notes Commands
- `/note` - Save a note
- `/notes` - List all notes
- `/clear` - Delete a note
- `/clearnotes` - Delete all notes
- Use `#note_name` to retrieve a note

## Approval Commands
- `/approve` - Approve a user
- `/disapprove` - Disapprove a user
- `/approved` - List all approved users
- `/approval` - Check if a user is approved

## Federation Commands
- `/newfed` - Create a new federation
- `/joinfed` - Join a federation
- `/leavefed` - Leave a federation
- `/fedinfo` - Get information about a federation
- `/fban` - Ban a user from all groups in the federation
- `/unfban` - Unban a user from the federation
- `/fedadmins` - List federation admins
- `/fedchats` - List all chats in the federation

## Anti-Flood Commands
- `/setflood` - Set flood limit
- `/flood` - Check current flood settings

## CAPTCHA Commands
- `/captcha` - Enable/disable CAPTCHA
- `/setcaptcha` - Configure CAPTCHA settings