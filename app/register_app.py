import streamlit as st
import bcrypt
import dbs
import qrcode
from io import BytesIO
from PIL import Image


def validate_email(email):
    """Validate email format and check if it already exists."""
    import re
    # Simple email format validation
    pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    if not re.match(pattern, email):
        return False, "Invalid email format."

    # Check if email already exists (case-insensitive)
    user = dbs.get_user_by_email(email)
    if user:
        return False, "Email already registered."

    return True, ""


def validate_username(username):
    """Validate username and check if it already exists."""
    if len(username) < 3:
        return False, "Username must be at least 3 characters."

    # Case-insensitive username check
    users = dbs.get_users()
    if any(u['Username'].lower() == username.lower() for u in users):
        return False, "Username already taken."

    return True, ""


def validate_password(password, confirm_password):
    """Validate password strength and match."""
    if password != confirm_password:
        return False, "Passwords do not match."

    if len(password) < 8:
        return False, "Password must be at least 8 characters."

    # Check for at least one uppercase, one lowercase, and one number
    if not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter."

    if not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter."

    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one number."

    return True, ""


def register_user(username, email, password, role, project_id):
    """Register a new user and add them to the database."""
    # Hash the password
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    # Add user to the database
    dbs.add_user(email, username, hashed_password, role="User", active=True)

    # Only create a welcome chat for regular users
    if role == "User":
        # Create an initial chat for the user
        dbs.add_chat(
            user_id=dbs.get_user_by_email(email)['UserID'],
            chat_name=f"Welcome Chat for {username}",
            chat_description="Your first chat in VoxPopuli",
            project_id=project_id
        )

    return email, role


def generate_qr_code(user_data):
    """Generate a QR code for user registration."""
    # Create QR code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(user_data)
    qr.make(fit=True)

    # Create an image from the QR Code
    img = qr.make_image(fill_color="black", back_color="white")

    # Save to BytesIO object
    buffered = BytesIO()
    img.save(buffered, format="PNG")

    return buffered


def register_page():
    """Display the registration page with form."""
    st.title("Register for VoxPopuli 🗣️")
    st.markdown("Create your account to get started with VoxPopuli.")

    # Initialize registration type state if it doesn't exist
    if "registration_type" not in st.session_state:
        st.session_state.registration_type = None

    # Initialize registration success state if it doesn't exist
    if "registration_success" not in st.session_state:
        st.session_state.registration_success = False
    if "registered_role" not in st.session_state:
        st.session_state.registered_role = None
    if "qr_generated" not in st.session_state:
        st.session_state.qr_generated = False
    if "user_data" not in st.session_state:
        st.session_state.user_data = None

    # If already registered successfully, just show the success message and button
    if st.session_state.registration_success:
        st.success("Registration successful! You can now log in.")
        if st.button("Back to Login Page", key="back_to_login"):
            st.session_state.registration_mode = False
            st.session_state.registration_success = False
            st.session_state.registered_role = None
            st.session_state.registration_type = None
            st.session_state.qr_generated = False
            st.session_state.user_data = None
            st.rerun()
        return

    # If registration type not selected yet, show the selection buttons
    if st.session_state.registration_type is None:
        st.markdown("### Choose Registration Type")

        col1, col2 = st.columns(2)

        with col1:
            if st.button("Register as User", use_container_width=True):
                st.session_state.registration_type = "User"
                st.rerun()

        with col2:
            if st.button("Register as Researcher", use_container_width=True):
                st.session_state.registration_type = "Researcher"
                st.rerun()

        # Information about the different roles
        with st.expander("What's the difference?"):
            st.markdown("""
            **User Role**:
            - Participate in research projects
            - Contribute to conversations
            - Donate your data for research purposes

            **Researcher Role**:
            - Lead research projects
            - Analyze user conversations and data
            - Manage users and data collection
            - Create reports and insights
            """)

        # Back button
        if st.button("Back to Login", key="reg_type_back"):
            st.session_state.registration_mode = False
            st.rerun()

        return

    # Different registration flows based on role
    if st.session_state.registration_type == "User":
        # User Registration Form
        with st.form("user_registration_form"):
            st.subheader("Register as User")

            # Form fields for users
            username = st.text_input("Username", key="user_username")
            email = st.text_input("Email", key="user_email")
            password = st.text_input("Password", type="password", key="user_password")
            confirm_password = st.text_input("Confirm Password", type="password", key="user_confirm_password")

            # Project name input
            project_name = st.text_input("Project Name to Join", key="user_project_name",
                                         help="Enter the name of the project you want to join")

            # Terms and conditions
            terms_agree = st.checkbox("I agree to the Terms and Conditions", key="user_terms")

            # Submit button
            submit_button = st.form_submit_button("Generate Registration QR Code")

            if submit_button:
                if not terms_agree:
                    st.error("You must agree to the Terms and Conditions.")
                elif not username or not email or not password or not confirm_password or not project_name:
                    st.error("Please fill in all required fields.")
                else:
                    # Validate inputs
                    is_valid_email, email_error = validate_email(email)
                    if not is_valid_email:
                        st.error(email_error)
                    else:
                        is_valid_username, username_error = validate_username(username)
                        if not is_valid_username:
                            st.error(username_error)
                        else:
                            is_valid_password, password_error = validate_password(password, confirm_password)
                            if not is_valid_password:
                                st.error(password_error)
                            else:
                                # All validations passed, register the user
                                user_email, user_role = register_user(username, email, password, "User", project_name)

                                # Create user data for QR code - in production this would be encrypted
                                user_data = f"Username:{username}|Email:{email}|Project:{project_name}"
                                st.session_state.user_data = user_data

                                # Mark registration as successful and QR code as generated
                                st.session_state.registration_success = True
                                st.session_state.registered_role = "User"
                                st.session_state.qr_generated = True
                                st.rerun()
    else:
        # Researcher Registration Form
        with st.form("researcher_registration_form"):
            st.subheader("Register as Researcher")

            # Form fields
            username = st.text_input("Username", key="reg_username")
            email = st.text_input("Email", key="reg_email")
            password = st.text_input("Password", type="password", key="reg_password")
            confirm_password = st.text_input("Confirm Password", type="password", key="reg_confirm")

            # Researcher-specific fields
            project_id = st.text_input("Project ID (Optional)", key="reg_project")

            # Terms and conditions checkbox
            terms_agree = st.checkbox("I agree to the Terms and Conditions", key="reg_terms")

            # Submit button
            submit_button = st.form_submit_button("Register")

            if submit_button:
                if not terms_agree:
                    st.error("You must agree to the Terms and Conditions.")
                elif not username or not email or not password or not confirm_password:
                    st.error("Please fill in all required fields.")
                else:
                    # Validate inputs
                    is_valid_email, email_error = validate_email(email)
                    if not is_valid_email:
                        st.error(email_error)
                    else:
                        is_valid_username, username_error = validate_username(username)
                        if not is_valid_username:
                            st.error(username_error)
                        else:
                            is_valid_password, password_error = validate_password(password, confirm_password)
                            if not is_valid_password:
                                st.error(password_error)
                            else:
                                # All validations passed, register the user
                                user_email, user_role = register_user(username, email, password, "Researcher", project_id)

                                # Mark registration as successful
                                st.session_state.registration_success = True
                                st.session_state.registered_role = "Researcher"
                                st.rerun()

    # Additional information (only shown before successful registration)
    st.markdown("---")

    # Change registration type button
    if st.button("Change Registration Type"):
        st.session_state.registration_type = None
        st.rerun()

    # Back button outside the form
    if st.button("Back to Login", key="reg_back"):
        st.session_state.registration_mode = False
        st.session_state.registration_type = None
        st.rerun()