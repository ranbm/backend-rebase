import logging

from flask import Blueprint, Response, request
from datetime import datetime as dt, timedelta
from users.db_utils import execute_query_all
reports_api = Blueprint("reports", __name__)
logger = logging.getLogger("rbm_awesome_logger")


def build_ascii_table(data, highlight_hours=None):
    if highlight_hours is None:
        highlight_hours = set()

    lines = [
        "| Hour            | Views |",
        "|-----------------|-------|"
    ]
    for item in data:
        h, v = item["h"], item["v"]
        # build start/end with a trailing space for single-digit hours
        start_str = f"{h}:00" + (" " if h < 10 else "")
        end_h = (h + 1) % 24
        end_str   = f"{end_h}:00" + (" " if end_h < 10 else "")
        mark      = " [*]" if h in highlight_hours else ""

        # now pad the *entire* cell to width 17
        hour_cell = f"{start_str}-{end_str}{mark}"
        lines.append(f"| {hour_cell:<15} | {v:<5} |")

    lines.append("|-----------------|-------|")
    return "\n".join(lines)

@reports_api.route("/<page>", methods=["GET"])
def get_report(page):
    try:
        now_arg = request.args.get("now")
        order = request.args.get("order", "asc").lower()
        take = request.args.get("take", type=int)

        if now_arg:
            try:
                now_hour = dt.strptime(now_arg, "%Y-%m-%dT%H:%M:%S").replace(minute=0, second=0, microsecond=0)
            except ValueError:
                return Response("Invalid datetime format", status=400)
        else:
            now_hour = dt.utcnow().replace(minute=0, second=0, microsecond=0)

        start = now_hour - timedelta(days=1)
        end = now_hour - timedelta(hours=1)

        query = f"""
            SELECT hour_start, view_count
              FROM page_hourly_views
             WHERE page_id = %s
               AND hour_start >= %s
               AND hour_start <= %s
             ORDER BY hour_start {"DESC" if order == "desc" else "ASC"}
        """
        
        try:
            rows = execute_query_all(query, (page, start, end))
        except Exception as e:
            logger.error(f"Database error: {str(e)}")
            return Response("Database error", status=500)

        data = [{"h": hs.hour, "v": vc} for hs, vc in rows]

        if take is not None:
            data = data[:take]

        highlight_hours = {item["h"] for item in data if item["h"] >= start.hour}

        table = build_ascii_table(data, highlight_hours)
        return Response(table, mimetype="text/plain")
    
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return Response("Internal server error", status=500)
