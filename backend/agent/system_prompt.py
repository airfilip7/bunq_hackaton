"""Assembles the full system prompt for the bunq Nest chat agent."""

from __future__ import annotations

from backend.prompts import COACHING_AGENT, DISCLAIMER
from backend.projection import DEPOSIT_FRACTION, HEADROOM_BAND, NIBUD_ANNUAL_FACTOR


def build_system_prompt(user_id: str, storage) -> str:
    profile = storage.get_profile(user_id)

    sections = [COACHING_AGENT, DISCLAIMER]

    if profile is not None:
        profile_lines: list[str] = ["## User Profile Snapshot"]

        if profile.payslip:
            p = profile.payslip
            profile_lines.append("### Income (payslip)")
            if p.gross_monthly_eur is not None:
                profile_lines.append(f"- Gross monthly: €{p.gross_monthly_eur:,.2f}")
            if p.net_monthly_eur is not None:
                profile_lines.append(f"- Net monthly: €{p.net_monthly_eur:,.2f}")
            if p.employer_name is not None:
                profile_lines.append(f"- Employer: {p.employer_name}")

        if profile.target:
            t = profile.target
            profile_lines.append("### Target Property")
            profile_lines.append(f"- Funda URL: {t.funda_url}")
            profile_lines.append(f"- Price: €{t.price_eur:,.2f}")
            if t.address is not None:
                profile_lines.append(f"- Address: {t.address}")

        if profile.projection:
            pr = profile.projection
            profile_lines.append("### Current Projection")
            profile_lines.append(f"- Savings now: €{pr.savings_now_eur:,.2f}")
            profile_lines.append(f"- Deposit target: €{pr.deposit_target_eur:,.2f}")
            profile_lines.append(f"- Gap: €{pr.gap_eur:,.2f}")
            profile_lines.append(f"- Monthly savings rate: €{pr.monthly_savings_eur:,.2f}")
            profile_lines.append(f"- Months to goal: {pr.months_to_goal}")
            lo, hi = pr.headroom_range_eur
            profile_lines.append(f"- Mortgage headroom range: €{lo:,} – €{hi:,} (per Nibud norms)")

        if len(profile_lines) > 1:
            sections.append("\n".join(profile_lines))

    deposit_pct = int(DEPOSIT_FRACTION * 100)
    band_pct = int(HEADROOM_BAND * 100)
    nibud_section = (
        "## Nibud Norms Reminder\n"
        f"Borrowing capacity is estimated using a ~{NIBUD_ANNUAL_FACTOR}× gross annual income "
        f"multiplier with a ±{band_pct}% band, always presented as a range. "
        f"Deposit target is {deposit_pct}% of property price (10% eigen inleg + 4% kosten koper). "
        "Every borrowing figure must be attributed \"per Nibud norms\"."
    )
    sections.append(nibud_section)

    tool_section = (
        "## Tool Usage Rules\n"
        "Read-only tools (get_bunq_transactions, get_bunq_buckets, get_funda_property, "
        "compute_projection, update_target_property) execute automatically without user confirmation.\n\n"
        "Write tools (propose_move_money, propose_create_bucket) require explicit user approval "
        "before any side effect runs. For any action that changes money, you MUST call the "
        "appropriate propose_* tool. Do NOT describe the action in prose instead of calling the tool.\n\n"
        "When the user pastes a Funda URL or asks to look at a different property, call "
        "update_target_property with the new URL. This will update their profile, recalculate "
        "projections, and you should then present the updated numbers to the user."
    )
    sections.append(tool_section)

    return "\n\n".join(sections)
