from datetime import date


class BrokerCommsService:
    """
    Generates professional broker communication templates.
    In production, this would integrate with email APIs (SendGrid, etc.)
    or a real AI model for dynamic content generation.
    """

    def generate_check_call(self, dispatch_data: dict) -> dict:
        driver = dispatch_data.get("driver_name", "our driver")
        broker = dispatch_data.get("broker_name", "Broker")
        origin = f"{dispatch_data.get('origin_city', '')}, {dispatch_data.get('origin_state', '')}"
        dest = f"{dispatch_data.get('destination_city', '')}, {dispatch_data.get('destination_state', '')}"
        status = dispatch_data.get("status", "en_route_pickup")

        templates = {
            "en_route_pickup": f"Hi {broker} team,\n\nThis is a check call for load {dispatch_data.get('load_ref', '')}.\n\n{driver} is currently en route to pickup at {origin}. ETA is on schedule.\n\nWill update once loaded.\n\nThank you,\n{dispatch_data.get('company_name', 'Carrier')}",
            "at_pickup": f"Hi {broker} team,\n\n{driver} has arrived at {origin} for pickup on load {dispatch_data.get('load_ref', '')}.\n\nCurrently waiting to be loaded. Will confirm once loaded and rolling.\n\nThank you,\n{dispatch_data.get('company_name', 'Carrier')}",
            "loaded": f"Hi {broker} team,\n\n{driver} is loaded and rolling on load {dispatch_data.get('load_ref', '')}.\n\nPickup: {origin}\nDelivery: {dest}\n\nWill provide next check call en route.\n\nThank you,\n{dispatch_data.get('company_name', 'Carrier')}",
            "en_route_delivery": f"Hi {broker} team,\n\nCheck call for load {dispatch_data.get('load_ref', '')}.\n\n{driver} is en route to delivery at {dest}. Running on schedule.\n\nWill confirm upon arrival.\n\nThank you,\n{dispatch_data.get('company_name', 'Carrier')}",
            "delivered": f"Hi {broker} team,\n\nLoad {dispatch_data.get('load_ref', '')} has been delivered to {dest}.\n\n{driver} confirmed delivery. POD will be submitted shortly.\n\nPlease process payment per our agreement.\n\nThank you,\n{dispatch_data.get('company_name', 'Carrier')}",
        }

        template = templates.get(status, templates["en_route_pickup"])
        subject = f"Check Call - Load {dispatch_data.get('load_ref', '')} - {status.replace('_', ' ').title()}"

        return {
            "subject": subject,
            "body": template,
            "status": status,
        }

    def generate_rate_confirmation_request(self, load_data: dict) -> dict:
        broker = load_data.get("broker_name", "Broker")
        origin = f"{load_data.get('origin_city', '')}, {load_data.get('origin_state', '')}"
        dest = f"{load_data.get('destination_city', '')}, {load_data.get('destination_state', '')}"
        rate = load_data.get("rate_total", 0)
        company = load_data.get("company_name", "Carrier")
        mc = load_data.get("carrier_mc", "")

        body = f"Hi {broker} team,\n\nPlease send the rate confirmation for the following load:\n\nOrigin: {origin}\nDestination: {dest}\nAgreed Rate: ${rate:.2f}\nCarrier: {company}\nMC#: {mc}\n\nWe are ready to dispatch upon receipt of the rate con.\n\nThank you,\n{company}"
        return {
            "subject": f"Rate Confirmation Request - {origin} to {dest}",
            "body": body,
        }

    def generate_invoice_reminder(self, invoice_data: dict) -> dict:
        broker = invoice_data.get("broker_name", "Broker")
        amount = invoice_data.get("amount", 0)
        due_date = invoice_data.get("due_date", "")
        inv_id = invoice_data.get("invoice_id", "")
        company = invoice_data.get("company_name", "Carrier")
        days_overdue = invoice_data.get("days_overdue", 0)

        if days_overdue > 0:
            urgency = f"This invoice is now {days_overdue} days past due. "
        else:
            urgency = ""

        body = f"Hi {broker} team,\n\n{urgency}This is a friendly reminder regarding invoice #{inv_id} for ${amount:.2f}, due on {due_date}.\n\nPlease process payment at your earliest convenience. If payment has already been sent, please disregard this message.\n\nThank you,\n{company}"
        return {
            "subject": f"Payment Reminder - Invoice #{inv_id} - ${amount:.2f}",
            "body": body,
        }
