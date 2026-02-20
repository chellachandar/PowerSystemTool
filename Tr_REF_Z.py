import math
import pandas as pd

class REF_ESI_Optimizer:

    def __init__(
        self,
        mva,
        hv_kv,
        bus_fault_ka,
        ct_ratios,
        rct,
        rlead,
        relay_va,
        ir,
        existing_vk=None
    ):

        self.mva = mva
        self.hv_kv = hv_kv
        self.bus_fault_ka = bus_fault_ka
        self.ct_ratios = ct_ratios
        self.rct = rct
        self.rlead = rlead
        self.relay_va = relay_va
        self.ir = ir
        self.existing_vk = existing_vk

    # ---------------------------------------------------
    # 1️⃣ FULL LOAD CURRENT
    # ---------------------------------------------------
    def full_load_current(self):
        return (self.mva * 1000) / (math.sqrt(3) * self.hv_kv)

    # ---------------------------------------------------
    # 2️⃣ ASSIGNED MAX THROUGH FAULT CURRENT
    # ---------------------------------------------------
    def through_fault_current(self):
        return self.bus_fault_ka * 1000

    # ---------------------------------------------------
    # 3️⃣ STABILITY VOLTAGE (ESI CORRECT)
    # Vs = I_sec × (Rct + Rlead)
    # ---------------------------------------------------
    def stability_voltage(self, ifault, ct):
        isec = ifault / ct
        return isec * (self.rct + self.rlead)

    # ---------------------------------------------------
    # 4️⃣ STABILISING RESISTOR
    # ---------------------------------------------------
    def stabilising_resistor(self, vs):
        return vs / self.ir

    # ---------------------------------------------------
    # 5️⃣ MINIMUM REQUIRED KNEE POINT
    # Vk ≥ 2 × Vs
    # ---------------------------------------------------
    def required_vk(self, vs):
        return 2 * vs

    # ---------------------------------------------------
    # 6️⃣ RECOMMENDED VK (1.5 SAFETY)
    # ---------------------------------------------------
    def recommended_vk(self, vk_min):
        return 1.5 * vk_min

    # ---------------------------------------------------
    # 7️⃣ LOAD ADEQUACY CHECK
    # ---------------------------------------------------
    def load_check(self, ct, ifl):
        return ct >= ifl

    # ---------------------------------------------------
    # MASTER EVALUATION
    # ---------------------------------------------------
    def evaluate(self):

        ifl = self.full_load_current()
        ifault = self.through_fault_current()

        results = []

        for ct in self.ct_ratios:

            load_ok = self.load_check(ct, ifl)

            vs = self.stability_voltage(ifault, ct)
            rst = self.stabilising_resistor(vs)
            vk_min = self.required_vk(vs)
            vk_rec = self.recommended_vk(vk_min)

            stability_margin = None
            verdict = "—"

            if self.existing_vk:
                stability_margin = self.existing_vk / vk_min
                verdict = "PASS" if self.existing_vk >= vk_min else "FAIL"

            results.append({
                "CT Ratio": ct,
                "Load Adequate": "YES" if load_ok else "NO",
                "Full Load Current (A)": round(ifl,2),
                "Through Fault (A)": round(ifault,2),
                "Secondary Fault (A)": round(ifault/ct,3),
                "Stability Voltage Vs (V)": round(vs,2),
                "Stabilising Resistor Rst (Ω)": round(rst,2),
                "Vk Minimum (V)": round(vk_min,2),
                "Vk Recommended (V)": round(vk_rec,2),
                "Stability Margin": round(stability_margin,2) if stability_margin else "—",
                "Verdict": verdict
            })

        df = pd.DataFrame(results)

        # Remove CTs that fail load adequacy
        df_valid = df[df["Load Adequate"] == "YES"]

        if not df_valid.empty:
            recommended_ct = df_valid.iloc[0]["CT Ratio"]
        else:
            recommended_ct = None

        return df, recommended_ct
