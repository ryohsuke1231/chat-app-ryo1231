import os
import requests
def send_simple_message():
  	return requests.post(
  		"https://api.mailgun.net/v3/sandbox3f4207d9855b4aadab7ddca3c48cd7fc.mailgun.org/messages",
  		auth=("api", "9b3854464ee761f76a7ca4db49496438-6d5bd527-f1700dd6"),
  		data={"from": "Mailgun Sandbox <postmaster@sandbox3f4207d9855b4aadab7ddca3c48cd7fc.mailgun.org>",
			"to": "Watanabe Ryosuke <z704626b@fcs.ed.jp>",
  			"subject": "Hello Watanabe Ryosuke",
  			"text": "Congratulations Watanabe Ryosuke, you just sent an email with Mailgun! You are truly awesome!"})
if __name__ == "__main__":
	send_simple_message()
	print("Email sent successfully!")
else:
	print("This script is not meant to be imported as a module.")
	print("Please run it directly to send an email.")