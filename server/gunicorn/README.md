# Server side
The server crawls the data needed and answers RESTful request
USE PYTHON 3.7

# REST API
Set a new RIOT API key (will be used as long as we have a 24 hours expiring developer key)
```
    [PUT] /set_api_key "data=<a api key>"
```

# Dot env
Here are the variables to set in the .env file to make the program work
```
# environments variables

# #Following are the setting to send the suggestion emails
# mail-configuration (gmail example)
mail-server = "smtp.gmail.com"
# mail of an account with 'Allow less secure app' on (see https://myaccount.google.com/lesssecureapps)
mail-user = "<user>@gmail.com"
# password of that account
mail-pass = "<your password>"
mail-recipients = "<recipient1>@gmail.com <recipient2>@gmail.com"

# website secret key
secret-key = "<secret key>"

# details for admin login
hash-salt = "<32 bits salt in bytes>"
admin-user = "admin"
admin-hashed-pass = "<32 bits hashed password in bytes>"

```