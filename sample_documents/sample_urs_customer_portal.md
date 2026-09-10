# Sample User Requirement Specification — Customer Portal Registration

## 1. Purpose
This sample document demonstrates how TestBuddy converts a User Requirement Specification into source-grounded QA test cases.

## 2. Functional requirements

### REQ-001 User registration
The system shall allow a new customer to register using a unique email address, a password, and a one-time verification code.

### REQ-002 Email uniqueness
The system must reject registration when the email address is already registered and shall display a clear validation message without creating a duplicate account.

### REQ-003 Password validation
The system shall require passwords to contain at least eight characters, one uppercase letter, one lowercase letter, and one number.

### REQ-004 Verification expiry
The system shall expire a verification code after 10 minutes and shall allow the user to request a new verification code after expiry.

### REQ-005 Audit event
The system must record a registration-success audit event containing the customer identifier, timestamp, and event type after a registration is completed successfully.

## 3. Non-functional requirement

### NFR-001 Response time
The registration confirmation page should be displayed within three seconds for at least 95 percent of normal requests under the agreed test load.

## 4. Test design note
The generated test cases are drafts. QA analysts must confirm the final user interface, exact validation text, integration behaviour, test data, security controls, and environment configuration against the approved specifications and detailed design.
