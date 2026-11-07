import os
import uuid
import re
import csv
import io
import sqlite3

from PIL import Image, ImageOps
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    Response
)
from dotenv import load_dotenv

from database import (
    init_db,
    add_problem,
    get_all_problems,
    get_problem,
    get_problem_for_tracking,
    update_problem,
    update_email_status
)

from email_service import (
    init_mail,
    send_resolution_email
)


# ==========================================
# 1. APPLICATION CONFIGURATION
# ==========================================

load_dotenv()

app = Flask(__name__)

app.secret_key = os.getenv("SECRET_KEY", "floodguard-dev-fallback-key-2026")

app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

UPLOAD_FOLDER = os.path.join(app.root_path, "static", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# ==========================================
# 2. INITIALIZE SERVICES
# ==========================================

init_mail(app)
init_db()


# ==========================================
# 3. PHOTO VALIDATION AND STORAGE
# ==========================================

def save_complaint_photo(file):
    if not file or not file.filename:
        raise ValueError("Please capture or upload a photo of the flood incident.")

    try:
        # Verify actual image integrity
        image = Image.open(file.stream)
        image.verify()

        file.stream.seek(0)
        image = Image.open(file.stream)

        if image.format not in ["JPEG", "PNG", "WEBP"]:
            raise ValueError("Only JPEG, PNG and WEBP image formats are supported.")

        image = ImageOps.exif_transpose(image)
        image = image.convert("RGB")

        # Downscale ultra-high resolution photos to save bandwidth
        max_dim = 1920
        if max(image.size) > max_dim:
            image.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)

        # Generate unique filename
        filename = f"{uuid.uuid4().hex}.jpg"
        filepath = os.path.join(UPLOAD_FOLDER, filename)

        image.save(filepath, "JPEG", quality=85, optimize=True)

        return f"uploads/{filename}"

    except ValueError:
        raise
    except Exception as error:
        app.logger.exception("Photo processing failed")
        raise ValueError("Invalid or corrupted photo file. Please upload another image.") from error


# ==========================================
# 4. HOME / CITIZEN REPORTING PAGE
# ==========================================

@app.route("/")
def home():
    return render_template("index.html")


# ==========================================
# 5. USER PROBLEM SUBMISSION
# ==========================================

@app.route("/submit_problem", methods=["POST"])
def submit_problem():
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()
    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    location = request.form.get("location", "").strip()

    # Validate required basic fields
    if not all([name, email, title, description, location]):
        flash("Please fill in all required fields.", "error")
        return redirect(url_for("home"))

    # Validate field lengths
    if len(name) > 100 or len(title) > 150 or len(description) > 3000 or len(location) > 250:
        flash("One or more fields exceed maximum character limits.", "error")
        return redirect(url_for("home"))

    # Validate email format
    if len(email) > 254 or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        flash("Please enter a valid email address so we can update you on resolution.", "error")
        return redirect(url_for("home"))

    photo_path = None

    try:
        # Validate GPS coordinates
        lat_raw = request.form.get("latitude", "").strip()
        lon_raw = request.form.get("longitude", "").strip()
        acc_raw = request.form.get("accuracy", "").strip()

        if not lat_raw or not lon_raw:
            raise ValueError("Live GPS location is required. Please click 'Detect Live GPS Location' before submitting.")

        try:
            latitude = float(lat_raw)
            longitude = float(lon_raw)
            accuracy = float(acc_raw) if acc_raw else 15.0
        except ValueError:
            raise ValueError("Invalid GPS location data received. Please re-detect your location.")

        if not (-90 <= latitude <= 90):
            raise ValueError("Invalid GPS latitude coordinate.")

        if not (-180 <= longitude <= 180):
            raise ValueError("Invalid GPS longitude coordinate.")

        if not (0 < accuracy <= 10000):
            raise ValueError("Invalid GPS accuracy reading.")

        if accuracy > 100:
            raise ValueError("GPS signal is too weak (accuracy is beyond 100 meters). Please try again in an open outdoor area.")

        # Validate and store photo
        photo = request.files.get("photo")
        photo_path = save_complaint_photo(photo)

        # Store complaint in database
        problem_id = add_problem(
            name=name,
            email=email,
            title=title,
            description=description,
            location=location,
            latitude=latitude,
            longitude=longitude,
            accuracy=accuracy,
            photo_path=photo_path
        )

        flash(f"Incident reported successfully! Your Tracking ID is FG{problem_id}.", "success")

    except ValueError as error:
        # Cleanup uploaded file if submission fails
        if photo_path:
            filepath = os.path.join(UPLOAD_FOLDER, os.path.basename(photo_path))
            if os.path.exists(filepath):
                try:
                    os.remove(filepath)
                except Exception:
                    pass

        flash(str(error), "error")

    except Exception as error:
        app.logger.exception("Complaint submission failed")

        if photo_path:
            filepath = os.path.join(UPLOAD_FOLDER, os.path.basename(photo_path))
            if os.path.exists(filepath):
                try:
                    os.remove(filepath)
                except Exception:
                    pass

        flash("An unexpected error occurred while saving your report. Please try again.", "error")

    return redirect(url_for("home"))


# ==========================================
# 6. CITIZEN INCIDENT STATUS TRACKING
# ==========================================

@app.route("/track", methods=["GET", "POST"])
def track():
    problem = None
    searched = False

    if request.method == "POST":
        searched = True
        raw_id = request.form.get("tracking_id", "").strip().upper()
        email = request.form.get("email", "").strip()

        clean_id_str = raw_id.replace("FG", "").strip()

        if not clean_id_str.isdigit() or not email:
            flash("Please enter a valid Tracking ID (e.g. FG1) and the email used when reporting.", "error")
        else:
            problem_id = int(clean_id_str)
            problem = get_problem_for_tracking(problem_id, email)
            if not problem:
                flash(f"No incident found for Tracking ID '{raw_id}' registered under '{email}'.", "error")

    return render_template("track.html", problem=problem, searched=searched)


# ==========================================
# 7. AGENT LOGIN
# ==========================================

@app.route("/agent_login", methods=["GET", "POST"])
def agent_login():
    if session.get("agent_logged_in"):
        return redirect(url_for("agent_dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        correct_username = os.getenv("AGENT_USERNAME", "admin")
        correct_password = os.getenv("AGENT_PASSWORD", "admin123")

        if not correct_username or not correct_password:
            flash("Agent credentials are not configured in system settings.", "error")
            return redirect(url_for("agent_login"))

        if username == correct_username and password == correct_password:
            session.clear()
            session["agent_logged_in"] = True
            session["agent_username"] = username
            flash("Welcome to FloodGuard AI Agent Operations Portal.", "success")
            return redirect(url_for("agent_dashboard"))

        flash("Invalid agent username or password.", "error")

    return render_template("agent_login.html")


# ==========================================
# 8. AGENT DASHBOARD
# ==========================================

@app.route("/agent_dashboard")
def agent_dashboard():
    if not session.get("agent_logged_in"):
        flash("Please log in to access the agent dashboard.", "error")
        return redirect(url_for("agent_login"))

    problems = get_all_problems()

    stats = {
        "total": len(problems),
        "pending": sum(1 for p in problems if p["status"] == "Pending"),
        "in_progress": sum(1 for p in problems if p["status"] == "In Progress"),
        "completed": sum(1 for p in problems if p["status"] == "Completed")
    }

    return render_template(
        "agent_dashboard.html",
        problems=problems,
        stats=stats,
        agent_username=session.get("agent_username", "Agent")
    )


# ==========================================
# 9. UPDATE COMPLAINT STATUS
# ==========================================

@app.route("/update_problem/<int:problem_id>", methods=["POST"])
def update_status(problem_id):
    if not session.get("agent_logged_in"):
        return redirect(url_for("agent_login"))

    problem = get_problem(problem_id)
    if not problem:
        flash("Complaint incident record not found.", "error")
        return redirect(url_for("agent_dashboard"))

    status = request.form.get("status", "").strip()
    remarks = request.form.get("remarks", "").strip()

    allowed_statuses = ["Pending", "In Progress", "Completed"]
    if status not in allowed_statuses:
        flash("Invalid status selection.", "error")
        return redirect(url_for("agent_dashboard"))

    if len(remarks) > 2000:
        flash("Resolution remarks exceed maximum length of 2000 characters.", "error")
        return redirect(url_for("agent_dashboard"))

    if status == "Completed" and not remarks:
        flash("Please provide resolution remarks explaining the actions taken before marking as completed.", "error")
        return redirect(url_for("agent_dashboard"))

    # Update database
    update_problem(problem_id, status, remarks)

    # Send resolution email if newly marked Completed
    if status == "Completed" and problem["status"] != "Completed":
        try:
            updated_problem = get_problem(problem_id)
            send_resolution_email(updated_problem)
            update_email_status(problem_id, "Sent")
            flash("Incident marked as Completed and resolution email dispatched to citizen.", "success")
        except Exception as error:
            app.logger.exception("Resolution email notification failed")
            update_email_status(problem_id, "Failed")
            flash(f"Incident status updated to Completed, but email notification failed: {error}", "error")
    else:
        flash(f"Incident FG{problem_id} status updated to '{status}'.", "success")

    return redirect(url_for("agent_dashboard"))


# ==========================================
# 10. RETRY FAILED EMAIL
# ==========================================

@app.route("/retry_email/<int:problem_id>", methods=["POST"])
def retry_email(problem_id):
    if not session.get("agent_logged_in"):
        return redirect(url_for("agent_login"))

    problem = get_problem(problem_id)
    if not problem:
        flash("Incident record not found.", "error")
        return redirect(url_for("agent_dashboard"))

    if problem["status"] != "Completed":
        flash("Resolution emails can only be sent for Completed incidents.", "error")
        return redirect(url_for("agent_dashboard"))

    if problem["email_status"] == "Sent":
        flash("Resolution notification has already been successfully delivered.", "error")
        return redirect(url_for("agent_dashboard"))

    try:
        send_resolution_email(problem)
        update_email_status(problem_id, "Sent")
        flash(f"Resolution email for FG{problem_id} successfully dispatched!", "success")
    except Exception as error:
        app.logger.exception("Email retry failed")
        update_email_status(problem_id, "Failed")
        flash(f"Failed to send email: {error}", "error")

    return redirect(url_for("agent_dashboard"))


# ==========================================
# 11. EXPORT INCIDENTS TO CSV
# ==========================================

@app.route("/export_csv")
def export_csv():
    if not session.get("agent_logged_in"):
        flash("Please log in to export incident reports.", "error")
        return redirect(url_for("agent_login"))

    problems = get_all_problems()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Incident ID",
        "Date Reported",
        "Citizen Name",
        "Email",
        "Title",
        "Location",
        "Latitude",
        "Longitude",
        "GPS Accuracy (m)",
        "Status",
        "Agent Remarks",
        "Email Delivery Status"
    ])

    for p in problems:
        writer.writerow([
            f"FG{p['id']}",
            p['created_at'] if p['created_at'] else "N/A",
            p['name'],
            p['email'],
            p['title'],
            p['location'],
            p['latitude'] if p['latitude'] is not None else "",
            p['longitude'] if p['longitude'] is not None else "",
            p['accuracy'] if p['accuracy'] is not None else "",
            p['status'],
            p['remarks'],
            p['email_status']
        ])

    response = Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=floodguard_incidents.csv"}
    )
    return response


# ==========================================
# 12. AGENT LOGOUT
# ==========================================

@app.route("/logout")
def logout():
    session.clear()
    flash("You have safely logged out.", "success")
    return redirect(url_for("agent_login"))


# ==========================================
# 13. ERROR HANDLERS
# ==========================================

@app.errorhandler(413)
def file_too_large(error):
    flash("Uploaded photo size exceeds 5 MB. Please upload a smaller image.", "error")
    return redirect(url_for("home"))


@app.errorhandler(404)
def not_found(error):
    return render_template("index.html"), 404


# ==========================================
# 14. RUN APPLICATION
# ==========================================

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
