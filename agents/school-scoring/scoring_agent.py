import math

class ScoringAgent:

    def __init__(self):

        self.subject_map = {
            "Computer Science": ["computer","software","ai","data","backend","developer","yazılım"],
            "Engineering": ["engineer","mechanical","robot","elektronik","makine","aerospace"],
            "Business and Economics": ["finance","business","economics","marketing","controller"],
            "Life Sciences": ["biology","medicine","health"],
            "Physical Sciences": ["physics","chemistry"],
        }

    def rank_score(self, rank):

        if not rank or rank <= 0:
            return 0.15

        if rank <= 50:
            return 1.0
        elif rank <= 200:
            return 0.9
        elif rank <= 500:
            return 0.8
        elif rank <= 800:
            return 0.7
        elif rank <= 1200:
            return 0.6
        elif rank <= 1500:
            return 0.5
        else:
            return 0.15

    def get_category(self, text):
        text_lower = text.lower()
        for subject, keywords in self.subject_map.items():
            if any(k in text_lower for k in keywords):
                return subject
        return None

    def department_match_score(self, department, position, world_rank, global_score):

        department = department.lower()
        position = position.lower()
        
        # düşük üniversite + global firma cezası flag'i
        is_low_tier_global = False
        if global_score >= 0.8 and (not world_rank or world_rank > 1000):
            is_low_tier_global = True

        # Direkt kelime eşleşmesi
        if any(k in position for k in department.split() if len(k) > 3):
            # Normalde 1.0, ama okulu kötüyse global firmada kendini tam ispatlayamaz (Örn: 0.90'a düşer)
            return 0.90 if is_low_tier_global else 1.0

        # Kategori bazlı eşleşme (örn: Data Scientist -> Computer Science)
        dept_cat = self.get_category(department)
        pos_cat = self.get_category(position)

        if dept_cat and pos_cat and dept_cat == pos_cat:
            # Katı ceza: 0.85 -> 0.65
            return 0.65 if is_low_tier_global else 0.85

        return 0.2

    def find_subject(self, position, subjects):

        pos = position.lower()

        for subject, keywords in self.subject_map.items():

            if any(k in pos for k in keywords):
                if not subjects:
                    return None
                for s in subjects:
                    if subject.lower() in s["name"].lower():
                        return s

        return None

    def company_factor(self, global_score, employer_country, school_country):
        
        is_global = global_score >= 0.8
        is_tr_school = (school_country == "TR")

        # Global Company (Apple, Google, vb.)
        if is_global:
            if school_country == employer_country:
                return 0.95
            else:
                return 0.85
        # National Company (TR firması)
        else:
            if school_country == employer_country:
                return 0.95
            else:
                return 0.80

    def run(self, input_data):

        position = input_data.get("position", "")
        department = input_data.get("department","")

        scraped = input_data.get("scraped_data", {})
        llm = input_data.get("llm_data", {})

        world_rank = None
        if "world_rank" in scraped and scraped["world_rank"]:
            world_rank = scraped["world_rank"].get("mid")

        subjects = scraped.get("subjects", [])

        global_score = llm.get("global_score", 0.0)
        employer_country = llm.get("employer_country", "")
        school_country = llm.get("school_country", "")

        university_score = self.rank_score(world_rank)

        subject = self.find_subject(position, subjects)

        if subject and "rank" in subject and subject["rank"]:
            subject_rank = subject["rank"].get("mid")
            subject_score = self.rank_score(subject_rank)
            subject_used = subject["name"]
        else:
            subject_score = 0
            subject_used = "N/A"

        dept_score = self.department_match_score(department, position, world_rank, global_score)

        company_score = self.company_factor(global_score, employer_country, school_country)

        # Yeni Ağırlıklar (Toplam 1.0)
        w_uni = 0.65
        w_sub = 0.15
        w_dept = 0.15
        w_comp = 0.05

        final = (
            w_uni * university_score +
            w_sub * subject_score +
            w_dept * dept_score +
            w_comp * company_score
        )

        # Alan Uyumsuzluğu (Field Mismatch) Kontrolü
        dept_cat = self.get_category(department)
        pos_cat = self.get_category(position)
        field_mismatch = (dept_cat != pos_cat) if (dept_cat and pos_cat) else False
        
        if field_mismatch:
            final *= 0.7

        final_score = round(min(final * 20, 20), 2)
        
        basis = (
            f"Uni:{university_score:.2f} "
            f"Sub:{subject_score:.2f} "
            f"Dept:{dept_score:.2f} "
            f"CompM:{company_score:.2f}"
            f" (W:{w_uni:.2f}/{w_sub:.2f}/{w_dept:.2f}/{w_comp:.2f})"
        )

        return {
            "status":"success",
            "position":position,
            "score_out_of_20":final_score,
            "subject_used":subject_used,
            "basis":basis
        }
