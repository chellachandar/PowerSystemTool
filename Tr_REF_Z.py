import math
import numpy as np

STANDARD_VS = [24, 36, 48, 60, 75, 85, 100, 120, 150, 200, 300, 380, 400]
STANDARD_RST = [1500, 2000, 2500, 3000, 4000, 5000, 6000, 7500, 8000, 9500, 10000]

class REFDesignOptimizer:

    def __init__(self, mva, hv_kv, stability_factor,
                 ct_taps, rct, rl, relay_va, ir,
                 existing_vk=None):

        self.mva = mva
        self.hv_kv = hv_kv
        self.stability_factor = stability_factor
        self.ct_taps = ct_taps
        self.rct = rct
        self.rl = rl
        self.relay_va = relay_va
        self.ir = ir
        self.existing_vk = existing_vk

    # ----------------------------------------------------
    # BASIC CALCULATIONS
    # ----------------------------------------------------

    def calculate_ifl(self):
        return (self.mva * 1000) / (math.sqrt(3) * self.hv_kv)

    def calculate_fault_current(self, ifl):
        return self.stability_factor * ifl

    def secondary_fault_current(self, if_primary, ct_ratio):
        return if_primary / ct_ratio

    def relay_resistance(self):
        return self.relay_va / (self.ir ** 2)

    def loop_resistance(self):
        return self.rct + self.rl + self.relay_resistance()

    def required_vs(self, if_sec):
        return if_sec * self.loop_resistance()

    def round_vs(self, vs_actual):
        for v in STANDARD_VS:
            if v >= vs_actual:
                return v
        return STANDARD_VS[-1]

    def required_rst(self, vs_selected):
        return vs_selected / self.ir

    def round_rst(self, rst_actual):
        for r in STANDARD_RST:
            if r >= rst_actual:
                return r
        return STANDARD_RST[-1]

    def vsa(self, rst_selected):
        return (self.relay_va / self.ir) + (self.ir * rst_selected)

    def required_vk(self, vsa):
        return 2 * vsa

    def recommended_vk(self, vk_min):
        return 1.5 * vk_min

    def peak_voltage(self, vk, if_sec):
        r_loop = self.loop_resistance()
        return 2 * math.sqrt(2 * vk * (if_sec * r_loop - vk))

    def metrosil_required(self, vp):
        return vp > 3000

    # ----------------------------------------------------
    # SCORING ENGINE
    # ----------------------------------------------------

    def score_ct(self, results):
        scores = []

        rst_values = [r["rst_selected"] for r in results]
        vs_values = [r["vs_selected"] for r in results]

        rst_min, rst_max = min(rst_values), max(rst_values)
        vs_min, vs_max = min(vs_values), max(vs_values)

        for r in results:

            # Stability margin
            if self.existing_vk:
                margin = self.existing_vk / r["vk_min"]
            else:
                margin = 1.5

            stability_score = min(margin / 1.5, 1)

            # Rst score
            if rst_max != rst_min:
                rst_score = 1 - ((r["rst_selected"] - rst_min) / (rst_max - rst_min))
            else:
                rst_score = 1

            # Vs score
            if vs_max != vs_min:
                vs_score = 1 - ((r["vs_selected"] - vs_min) / (vs_max - vs_min))
            else:
                vs_score = 1

            # Metrosil score
            metrosil_score = 0 if r["metrosil"] else 1

            total_score = (
                0.40 * stability_score +
                0.25 * rst_score +
                0.20 * vs_score +
                0.15 * metrosil_score
            )

            scores.append(total_score)

        return scores

    # ----------------------------------------------------
    # MASTER EXECUTION
    # ----------------------------------------------------

    def evaluate(self):

        ifl = self.calculate_ifl()
        if_primary = self.calculate_fault_current(ifl)

        results = []

        for ct in self.ct_taps:

            if_sec = self.secondary_fault_current(if_primary, ct)
            vs_actual = self.required_vs(if_sec)
            vs_selected = self.round_vs(vs_actual)

            rst_actual = self.required_rst(vs_selected)
            rst_selected = self.round_rst(rst_actual)

            vsa_value = self.vsa(rst_selected)
            vk_min = self.required_vk(vsa_value)
            vk_recommended = self.recommended_vk(vk_min)

            vp = None
            metrosil = None

            if self.existing_vk:
                vp = self.peak_voltage(self.existing_vk, if_sec)
                metrosil = self.metrosil_required(vp)

            results.append({
                "ct_ratio": ct,
                "ifl": ifl,
                "if_primary": if_primary,
                "if_secondary": if_sec,
                "vs_actual": vs_actual,
                "vs_selected": vs_selected,
                "rst_actual": rst_actual,
                "rst_selected": rst_selected,
                "vk_min": vk_min,
                "vk_recommended": vk_recommended,
                "vsa": vsa_value,
                "peak_voltage": vp,
                "metrosil": metrosil
            })

        scores = self.score_ct(results)

        for i, r in enumerate(results):
            r["score"] = scores[i]

        results_sorted = sorted(results, key=lambda x: x["score"], reverse=True)

        return results_sorted
