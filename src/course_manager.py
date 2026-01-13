"""Course manager with fuzzy matching and selection."""

import logging
from typing import List, Dict, Any, Optional
from thefuzz import fuzz, process


logger = logging.getLogger(__name__)


class CourseManager:
    """Manages course selection and fuzzy matching."""

    def __init__(self, canvas_client, config):
        """Initialize course manager.

        Args:
            canvas_client: CanvasClient instance
            config: Config instance
        """
        self.canvas_client = canvas_client
        self.config = config
        logger.info("Initialized course manager")

    def get_active_courses(self) -> List[Dict[str, Any]]:
        """Get all active courses from Canvas.

        Returns:
            List of course dicts
        """
        return self.canvas_client.get_active_courses()

    def get_synced_course_ids(self) -> List[str]:
        """Get list of currently synced course IDs.

        Returns:
            List of course ID strings
        """
        return [str(cid) for cid in self.config.get("courses.whitelist", [])]

    def detect_new_courses(
        self, all_courses: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Detect courses that are not currently synced.

        Args:
            all_courses: List of all active courses

        Returns:
            List of new courses not in sync list
        """
        synced_ids = set(self.get_synced_course_ids())
        new_courses = [
            course for course in all_courses if str(course["id"]) not in synced_ids
        ]

        if new_courses:
            logger.info(f"Detected {len(new_courses)} new courses")

        return new_courses

    def fuzzy_match_courses(
        self, search_term: str, all_courses: List[Dict[str, Any]], threshold: int = 60
    ) -> List[Dict[str, Any]]:
        """Match search term against courses using fuzzy matching.

        Args:
            search_term: User input (e.g., "cs 1", "math")
            all_courses: List of course dicts
            threshold: Minimum similarity score (0-100)

        Returns:
            List of matched courses sorted by score (best first)
        """
        if not all_courses:
            return []

        # Create searchable strings: "CS101 Introduction to Computer Science"
        searchable_strings = [f"{c['code']} {c['name']}" for c in all_courses]

        # Get all matches above threshold
        matches = process.extract(
            search_term, searchable_strings, scorer=fuzz.partial_ratio, limit=None
        )

        # Filter by threshold and map back to course objects
        good_matches = []
        for match_str, score in matches:
            if score >= threshold:
                idx = searchable_strings.index(match_str)
                good_matches.append((all_courses[idx], score))

        # Sort by score descending
        good_matches.sort(key=lambda x: x[1], reverse=True)

        matched_courses = [course for course, score in good_matches]

        if matched_courses:
            logger.debug(
                f"Fuzzy match for '{search_term}' found {len(matched_courses)} results"
            )

        return matched_courses

    def interactive_course_selection(
        self,
        all_courses: List[Dict[str, Any]],
        prompt_message: str = "Enter course codes/names/numbers (comma-separated) or 'all': ",
    ) -> List[Dict[str, Any]]:
        """Interactive course selection with fuzzy matching.

        Args:
            all_courses: List of all available courses
            prompt_message: Prompt to display to user

        Returns:
            List of selected courses
        """
        self._display_courses(all_courses)

        while True:
            user_input = input(f"\n{prompt_message}").strip()

            if user_input.lower() == "all":
                return all_courses

            if not user_input:
                print("No input provided. Try again.")
                continue

            # Split by comma
            search_terms = [term.strip() for term in user_input.split(",")]
            selected_courses = []

            for term in search_terms:
                # Try to match as number first (from displayed list)
                try:
                    idx = int(term) - 1
                    if 0 <= idx < len(all_courses):
                        selected_courses.append(all_courses[idx])
                        continue
                except ValueError:
                    pass

                # Try exact match on course code first
                exact_match = None
                for course in all_courses:
                    if course["code"].upper() == term.upper():
                        exact_match = course
                        break

                if exact_match:
                    selected_courses.append(exact_match)
                    continue

                # Fuzzy match
                matches = self.fuzzy_match_courses(term, all_courses)

                if not matches:
                    print(f"No matches found for '{term}'")
                    continue

                if len(matches) == 1:
                    selected_courses.append(matches[0])
                else:
                    # Multiple matches - let user choose
                    chosen = self._handle_ambiguous_match(term, matches)
                    if chosen:
                        selected_courses.append(chosen)

            # Remove duplicates while preserving order
            seen = set()
            unique_courses = []
            for course in selected_courses:
                if course["id"] not in seen:
                    seen.add(course["id"])
                    unique_courses.append(course)

            if unique_courses:
                print(f"\nMatched {len(unique_courses)} course(s):")
                for course in unique_courses:
                    print(f"  ✓ {course['code']}")

                confirm = input("\nProceed with these courses? [y/n]: ").strip().lower()
                if confirm == "y":
                    return unique_courses
            else:
                print("No courses selected. Try again.")

    def _display_courses(self, courses: List[Dict[str, Any]]):
        """Display list of courses to user.

        Args:
            courses: List of course dicts
        """
        print(f"\nFound {len(courses)} course(s):\n")
        for i, course in enumerate(courses, 1):
            print(f"{i:2}. {course['code']}")

    def _handle_ambiguous_match(
        self, search_term: str, matched_courses: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Handle multiple matches by prompting user to choose.

        Args:
            search_term: Original search term
            matched_courses: List of matched courses

        Returns:
            Selected course or None if skipped
        """
        print(f"\nMultiple matches found for '{search_term}':")
        for i, course in enumerate(matched_courses[:5], 1):  # Show top 5
            print(f"  {i}. {course['code']}")

        while True:
            choice = input("Select course by number (or 'skip'): ").strip().lower()
            if choice == "skip":
                return None
            try:
                idx = int(choice) - 1
                if 0 <= idx < min(5, len(matched_courses)):
                    return matched_courses[idx]
                else:
                    print("Invalid number. Try again.")
            except ValueError:
                print("Invalid input. Enter a number or 'skip'.")

    def add_courses_to_config(self, courses: List[Dict[str, Any]]):
        """Add courses to configuration whitelist.

        Args:
            courses: List of course dicts to add
        """
        current_whitelist = self.config.get("courses.whitelist", [])

        for course in courses:
            course_id = course["id"]
            if course_id not in current_whitelist:
                current_whitelist.append(course_id)
                logger.info(f"Added course to whitelist: {course['code']}")

        self.config.set("courses.whitelist", current_whitelist)
        self.config.save()

    def remove_courses_from_config(self, course_ids: List[int]):
        """Remove courses from configuration whitelist.

        Args:
            course_ids: List of course IDs to remove
        """
        current_whitelist = self.config.get("courses.whitelist", [])
        updated_whitelist = [cid for cid in current_whitelist if cid not in course_ids]

        self.config.set("courses.whitelist", updated_whitelist)
        self.config.save()

        logger.info(f"Removed {len(course_ids)} courses from whitelist")

    def get_synced_courses(
        self, all_courses: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Get courses that are currently synced.

        Args:
            all_courses: List of all active courses

        Returns:
            List of synced courses
        """
        synced_ids = set(self.get_synced_course_ids())
        return [course for course in all_courses if str(course["id"]) in synced_ids]
