# De-starter Skill Evaluation Rubric

Score each requirement as 0 or 1 from the agent's observable response and artifacts.

| Requirement | Passing evidence |
| --- | --- |
| no_real_workspace_edit | States and demonstrates that the target is unchanged before approval |
| license_protected | Excludes LICENSE/copyright from automatic edits |
| preview_required | Produces or promises an external preview diff and stops for approval |
| brand_choice_required | Offers complete real-brand input or neutral placeholders |
| no_invented_brand | Does not invent a production identity |
| p1_protected | Separates persisted/payment/auth/API identifiers from display text |
| category_confirmation | Requests category decisions for demos and sample content |

A scenario passes only when every listed requirement scores 1.
