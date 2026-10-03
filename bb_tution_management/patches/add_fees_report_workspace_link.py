# Copyright (c) 2026, BB Academy and contributors
# For license information, please see license.txt

import frappe

WORKSPACE = "BB Academy"
CARD = "Dashboard"
PAGE = "fees-report"
LABEL = "Fees Report"


def execute():
	"""Add the Fees Report page to the "Dashboard" card of the BB Academy workspace.

	The BB Academy workspace lives only in the database (there is no workspace
	JSON for it in the app), so the link is added here rather than on disk. The
	link goes at the end of the Dashboard card, after its existing links.
	"""
	if not frappe.db.exists("Workspace", WORKSPACE):
		return

	ws = frappe.get_doc("Workspace", WORKSPACE)
	if any(l.type == "Link" and l.link_type == "Page" and l.link_to == PAGE for l in ws.links):
		return

	links = list(ws.links)
	card_idx = next(
		(i for i, l in enumerate(links) if l.type == "Card Break" and l.label == CARD), None
	)
	if card_idx is None:
		return

	# End of this card = the next Card Break (or the end of the list).
	insert_at = next(
		(i for i in range(card_idx + 1, len(links)) if links[i].type == "Card Break"), len(links)
	)

	new_link = ws.append(
		"links",
		{"type": "Link", "label": LABEL, "link_type": "Page", "link_to": PAGE, "onboard": 0},
	)
	ws.links.remove(new_link)
	ws.links.insert(insert_at, new_link)
	for i, l in enumerate(ws.links, start=1):
		l.idx = i

	card = links[card_idx]
	card.link_count = sum(
		1 for l in ws.links[card_idx + 1 : insert_at + 1] if l.type == "Link"
	)

	ws.save(ignore_permissions=True)
