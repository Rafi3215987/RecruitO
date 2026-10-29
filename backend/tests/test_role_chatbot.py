import unittest

from app.graphs.role_chatbot import tools_for_role


class RoleChatbotAllowlistTests(unittest.TestCase):
    def test_each_role_receives_a_distinct_tool_allowlist(self):
        candidate = {item.name for item in tools_for_role("candidate", 11)}
        interviewer = {item.name for item in tools_for_role("interviewer", 22)}
        manager = {item.name for item in tools_for_role("hiring_manager", 33)}
        self.assertEqual(candidate, {"my_applications", "public_jobs"})
        self.assertEqual(interviewer, {"assigned_interviews", "assigned_interview_transcript"})
        self.assertEqual(manager, {"hiring_jobs", "job_profile", "application_ranking",
                                   "candidate_assessment", "hiring_interview_schedule"})
        self.assertFalse(candidate & interviewer)
        self.assertFalse(candidate & manager)
        self.assertFalse(interviewer & manager)

    def test_invalid_role_has_no_tools(self):
        self.assertEqual(tools_for_role("unknown", 1), [])

    def test_user_ids_are_not_tool_arguments(self):
        for role in ("candidate", "interviewer", "hiring_manager"):
            for item in tools_for_role(role, 50):
                self.assertNotIn("user_id", item.args_schema.model_fields)


if __name__ == "__main__":
    unittest.main()
