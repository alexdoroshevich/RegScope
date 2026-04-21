# Privacy Notice

_Last updated: 2026-04-21._

This notice explains how FedComment handles information. It applies to
hosted instances operated by the project maintainers. If you self-host the
FedComment software, your own instance is outside the scope of this
notice.

## TL;DR

- We do not track you.
- We do not set analytics or advertising cookies.
- We do not collect any personal information from visitors.
- We do not require accounts, logins, or payment.
- We display public-record comment data with submitter names **anonymised
  by default**; viewing original names requires an explicit opt-in per
  page session.

## 1. Information we do not collect

We **do not** collect, store, or process:

- Your name, email address, or any contact information.
- IP addresses beyond what your browser sends to the hosting provider for
  basic request routing (these are not retained in application logs).
- Cookies for analytics, advertising, profiling, or personalisation.
- Local storage or session storage in your browser (the application does
  not use either).
- Login credentials — there are no user accounts.
- Payment information — the Service is free and accepts no payments.
- Location data.
- Device identifiers.
- Referrer or clickstream data.

## 2. Information that may be processed

The only data the Service processes is:

- **Public comment data** fetched from US federal APIs (Federal Register,
  Regulations.gov). This may include submitter names, organisations, and
  comment text that were submitted as public record.
- **Basic request routing** — the hosting infrastructure may briefly
  observe your IP address and user-agent to route HTTP requests, as is
  unavoidable for any web service. We do not retain this information in
  application logs.

## 3. Public-record comment data (PII)

Comments submitted to federal regulatory dockets are public record under
5 U.S.C. § 553 and the Administrative Procedure Act. This means submitter
names are technically public. However, re-publishing this data on a
third-party platform may have implications under various privacy regimes
(including the EU General Data Protection Regulation and the California
Consumer Privacy Act).

To minimise the risk of harm to commenters, FedComment:

- **Anonymises submitter names by default** in the user interface,
  displaying a deterministic opaque handle (e.g. `Submitter #a3f2`) in
  place of real names.
- Requires users to **explicitly opt in** to view original names by
  toggling a visible setting. When they opt in, a warning banner reminds
  them they are viewing public-record data and accept responsibility for
  its use.
- **Does not send submitter names to the LLM** used for cluster labels or
  RAG answers. LLM prompts contain only anonymous comment text.
- **Does not expose submitter contact information** (email addresses,
  phone numbers) even when present in the source API response.

## 4. Takedown / erasure requests

If you believe the Service is displaying information about you in a way
that exceeds what the underlying public record provides, please contact
the project maintainers via the [SECURITY.md](SECURITY.md) contact
channel. The maintainers will review and, where appropriate, add an
exclusion for your submissions within a reasonable time.

Note that the primary public record lives at Regulations.gov — we do not
control that source. Requests to remove data from the public record itself
must be directed to the relevant US federal agency.

## 5. Third-party services

A hosted instance of FedComment may use:

- A cloud hosting provider (e.g. Fly.io, Render, Railway) for compute.
  The provider's own privacy practices apply to traffic routing.
- OpenAI's API (via litellm) for generating cluster labels and RAG
  answers. Requests sent to OpenAI contain only anonymised comment text
  and the user's question — no identifying information about the visitor.
  See OpenAI's API data-usage policy for details of their handling.

## 6. Children

The Service is not directed to children under the age of 13, and we do
not knowingly collect information from children. If you believe a child
has been exposed to the Service in a way that concerns you, please
contact the maintainers.

## 7. Changes

We may update this notice as the project evolves. The authoritative
version lives at `PRIVACY.md` in the main branch of the repository.
Material changes will be reflected in the "Last updated" date at the top.

## 8. Contact

For privacy-related questions or requests, see the contact channel in
[SECURITY.md](SECURITY.md).
