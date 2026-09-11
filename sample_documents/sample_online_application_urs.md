# User Requirement Specification — Online Customer Registration and Account Management Application

## 1. Document purpose

This synthetic User Requirement Specification is provided as a demonstration input for TestBuddy. It describes a public-facing online application that allows customers to register, verify their email address, sign in, manage their profile, and recover access to their account.

These requirements are intentionally generic and contain no real customer data, credentials, production URLs, or confidential implementation details.

## 2. Scope

The application shall support customer registration, email verification, authentication, account lockout, password reset, profile maintenance, and audit logging. The application shall be accessible through a modern web browser on desktop and mobile screen sizes.

## 3. Functional requirements

### REQ-001 Customer registration
The system shall allow a new customer to register by providing a unique email address, a password, and the customer's full name.

### REQ-002 Mandatory-field validation
The system must prevent registration when any mandatory field is empty and shall display a clear validation message beside each missing field.

### REQ-003 Email format validation
The system shall reject an email address that does not conform to the accepted email format and shall not create an account from invalid input.

### REQ-004 Email uniqueness
The system must reject registration when the email address is already registered and shall display a clear message without creating a duplicate account.

### REQ-005 Password policy
The system shall require passwords to contain at least eight characters, one uppercase letter, one lowercase letter, and one number.

### REQ-006 Password confirmation
The system shall require the password and confirmation-password fields to match before registration can be completed.

### REQ-007 Verification code delivery
After valid registration details are submitted, the system shall send a one-time verification code to the registered email address.

### REQ-008 Verification code validation
The system shall activate the account only when the user submits the correct verification code within the code validity period.

### REQ-009 Verification-code expiry
The system shall expire a verification code after 10 minutes and shall allow the user to request a replacement code after expiry.

### REQ-010 Invalid verification attempts
The system shall reject an incorrect verification code, display a non-sensitive error message, and retain the account in an unverified state.

### REQ-011 Successful sign-in
The system shall allow a verified customer to sign in with the registered email address and correct password.

### REQ-012 Invalid sign-in
The system shall reject an incorrect email-and-password combination without revealing whether the email address exists.

### REQ-013 Account lockout
The system shall temporarily lock sign-in after five consecutive unsuccessful authentication attempts within a 15-minute period.

### REQ-014 Password reset request
The system shall allow a customer to request a password-reset link using the registered email address.

### REQ-015 Password-reset expiry
The system shall expire a password-reset link after 30 minutes and shall prevent reuse of a completed or expired link.

### REQ-016 Profile update
The system shall allow an authenticated customer to update the full name and preferred contact number, subject to field validation.

### REQ-017 Session timeout
The system shall end an authenticated session after 30 minutes of inactivity and shall require the customer to sign in again.

### REQ-018 Audit logging
The system must record successful registration, verification, sign-in, password reset, profile update, account lockout, and sign-out events with an event type and timestamp.

## 4. Non-functional requirements

### NFR-001 Response time
The system should display a normal page response within three seconds for at least 95 percent of requests under the agreed test load.

### NFR-002 Availability
The application should be available during the agreed service hours, excluding planned maintenance windows.

### NFR-003 Accessibility
The application should support keyboard navigation, visible focus indicators, readable labels, and meaningful validation messages.

### NFR-004 Security
The application must not display passwords, verification codes, reset tokens, or other authentication secrets in clear text in the user interface or audit-log message.

### NFR-005 Responsive layout
The application should remain usable on desktop and mobile viewport sizes without loss of required functionality.

## 5. Test design guidance

Test cases generated from this document are drafts for QA review. QA analysts must confirm exact field names, message text, browser support, email-delivery behaviour, security controls, accessibility criteria, integration dependencies, environment configuration, and final acceptance criteria against the approved solution design.

The demonstration should include happy paths, invalid inputs, boundary values such as eight-character passwords and five failed sign-in attempts, expired codes and links, duplicate registration, session timeout, accessibility checks, and security observations.
