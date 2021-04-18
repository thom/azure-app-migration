import logging
import azure.functions as func
import psycopg2
import os
from datetime import datetime
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail


def main(msg: func.ServiceBusMessage):

    notification_id = int(msg.get_body().decode('utf-8'))
    logging.info(
        f"Python ServiceBus queue trigger processed message: {notification_id}")

    # Get connection to database
    conn = psycopg2.connect(
        host=os.environ["POSTGRES_URL"],
        database=os.environ["POSTGRES_DB"],
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PW"]
    )
    logging.info(f"Successfully connected to {POSTGRES_DB}@{POSTGRES_URL}")

    try:
        # Get notification message and subject from database using the notification_id
        cur = conn.cursor()
        cmd = f"SELECT message, subject FROM notification WHERE id={notification_id}"
        cur.execute(cmd)
        logging.info(
            f"Notification ID {notification_id}: Get message and subject")

        for row in cur.fetchall():
            message = row[0]
            subject = row[1]

        if not message or not subject:
            error_message = f"Notification ID {notification_id}: No message or subject"
            logging.error(error_message)
            raise Exception(error_message)

        # Get attendees email and name
        cmd = f"SELECT first_name, last_name, email FROM attendee"
        cursor.execute(cmd)
        count = 0

        # TODO: Loop through each attendee and send an email with a personalized subject

        # TODO: Update the notification table by setting the completed date and updating the status with the total number of attendees notified

    except (Exception, psycopg2.DatabaseError) as error:
        logging.error(error)
    finally:
        # TODO: Close connection
        pass
