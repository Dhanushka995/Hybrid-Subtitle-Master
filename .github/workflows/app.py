import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import google.generativeai as genai
from openai import OpenAI
from deep_translator import GoogleTranslator
import threading
import time
import re
import os
import requests
import json

CONFIG_FILE = "hybrid_sub_config.json"

class HybridSubtitleApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Hybrid AI Subtitle Master v1.0")
        self.root.geometry("650x850")
        self.root.configure(bg="#1e272e")

        self.is_running = False
        self.provider_type = "Unknown"
        self.file_path = ""

        # --- UI ---
        tk.Label(root, text="HYBRID AI TRANSLATOR", bg="#1e272e", fg="#00d8d6", font=("Arial", 16, "bold")).pack(pady=15)

        tk.Label(root, text="Paste your API Key here (Auto-Detects Provider):", bg="#1e272e", fg="#d2dae2").pack(pady=(5, 0))
        self.api_var = tk.StringVar()
        self.api_var.trace_add("write", self.on_key_change)
        self.api_entry = tk.Entry(root, textvariable=self.api_var, width=65, show="*", bg="#485460", fg="white", borderwidth=0, font=("Consolas", 10))
        self.api_entry.pack(pady=5, ipady=6)

        self.key_status_lbl = tk.Label(root, text="Waiting for API Key...", bg="#1e272e", fg="#808e9b", font=("Arial", 9, "bold"))
        self.key_status_lbl.pack(pady=2)

        self.adv_frame = tk.Frame(root, bg="#2f3640", padx=10, pady=10)
        self.adv_frame.pack(pady=10, fill="x", padx=40)
        
        tk.Label(self.adv_frame, text="Base URL:", bg="#2f3640", fg="white").grid(row=0, column=0, sticky="w")
        self.base_url_var = tk.StringVar()
        tk.Entry(self.adv_frame, textvariable=self.base_url_var, width=50, bg="#1e272e", fg="white").grid(row=0, column=1, padx=10, pady=2)

        tk.Label(self.adv_frame, text="Model Name:", bg="#2f3640", fg="white").grid(row=1, column=0, sticky="w")
        self.model_var = tk.StringVar()
        tk.Entry(self.adv_frame, textvariable=self.model_var, width=50, bg="#1e272e", fg="white").grid(row=1, column=1, padx=10, pady=2)

        tk.Button(root, text="📂 Select English SRT File", command=self.open_file, bg="#0fb9b1", fg="white", font=("Arial", 10, "bold"), width=30).pack(pady=10)
        self.lbl_status_file = tk.Label(root, text="No file selected", bg="#1e272e", fg="#808e9b")
        self.lbl_status_file.pack()

        settings_frame = tk.Frame(root, bg="#1e272e")
        settings_frame.pack(pady=10)
        
        tk.Label(settings_frame, text="Chunk Size:", bg="#1e272e", fg="white").grid(row=0, column=0, padx=5)
        self.chunk_var = tk.StringVar(value="40")
        ttk.Combobox(settings_frame, textvariable=self.chunk_var, values=["10", "20", "30", "40", "50"], width=5).grid(row=0, column=1, padx=5)
        
        tk.Label(settings_frame, text="Language:", bg="#1e272e", fg="white").grid(row=0, column=2, padx=15)
        self.lang_var = tk.StringVar(value="Sinhala")
        ttk.Combobox(settings_frame, textvariable=self.lang_var, values=["Sinhala", "Tamil", "Hindi"], width=10).grid(row=0, column=3, padx=5)

        self.delay_enabled = tk.BooleanVar(value=True)
        tk.Checkbutton(settings_frame, text="Enable 15s Rate Limit Delay", variable=self.delay_enabled, bg="#1e272e", fg="#0be881", selectcolor="#1e272e").grid(row=1, column=0, columnspan=4, pady=10)

        tk.Label(settings_frame, text="Start from Chunk:", bg="#1e272e", fg="#ff9f43").grid(row=2, column=0, columnspan=2, pady=5, sticky="e")
        self.resume_var = tk.StringVar(value="1")
        tk.Entry(settings_frame, textvariable=self.resume_var, width=6, bg="#ff9f43", font=("Arial", 10, "bold")).grid(row=2, column=2, sticky="w", pady=5)

        self.log_box = tk.Text(root, height=10, width=75, bg="#000000", fg="#0be881", font=("Consolas", 9))
        self.log_box.pack(pady=5, padx=20)

        btn_frame = tk.Frame(root, bg="#1e272e")
        btn_frame.pack(pady=15)

        self.btn_start = tk.Button(btn_frame, text="START", command=self.start_process, bg="#0984e3", fg="white", font=("Arial", 12, "bold"), width=15, height=2)
        self.btn_start.grid(row=0, column=0, padx=10)

        self.btn_stop = tk.Button(btn_frame, text="STOP", command=self.stop_process, bg="#2d3436", fg="white", font=("Arial", 12, "bold"), width=15, height=2, state="disabled")
        self.btn_stop.grid(row=0, column=1, padx=10)

        self.btn_reset = tk.Button(btn_frame, text="Reset", command=self.reset_all, bg="#d63031", fg="white", font=("Arial", 12, "bold"), width=15, height=2)
        self.btn_reset.grid(row=0, column=2, padx=10)

        self.load_settings()

    def load_settings(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    data = json.load(f)
                    if data.get("api_key"): self.api_var.set(data["api_key"])
                    if data.get("base_url"): self.base_url_var.set(data["base_url"])
                    if data.get("model_name"): self.model_var.set(data["model_name"])
            except: pass

    def save_settings(self):
        data = {"api_key": self.api_var.get(), "base_url": self.base_url_var.get(), "model_name": self.model_var.get()}
        try:
            with open(CONFIG_FILE, "w") as f: json.dump(data, f)
        except: pass

    def log(self, text):
        self.log_box.insert(tk.END, "> " + text + "\n")
        self.log_box.see(tk.END)

    def on_key_change(self, *args):
        key = self.api_var.get().strip()
        if not key: 
            self.key_status_lbl.config(text="Waiting for API Key...", fg="#808e9b")
            return
        if key.startswith("AIza"):
            self.provider_type = "Gemini"
            self.key_status_lbl.config(text="✅ Detected: Google Gemini", fg="#0be881")
            self.base_url_var.set("N/A")
            self.model_var.set("gemini-1.5-flash")
        elif key.startswith("sk-or-"):
            self.provider_type = "OpenRouter"
            self.key_status_lbl.config(text="✅ Detected: OpenRouter", fg="#0be881")
            self.base_url_var.set("https://openrouter.ai/api/v1")
            self.model_var.set("google/gemini-2.0-flash-lite-preview-02-05:free")
        elif key.startswith("gsk_"):
            self.provider_type = "Groq"
            self.key_status_lbl.config(text="✅ Detected: Groq API", fg="#0be881")
            self.base_url_var.set("https://api.groq.com/openai/v1")
            self.model_var.set("llama-3.3-70b-versatile")
        else:
            self.provider_type = "OpenAI_Compatible"
            self.key_status_lbl.config(text="⚠️ Unknown Key: Enter URL & Model manually", fg="#ffdd59")

    def open_file(self):
        self.file_path = filedialog.askopenfilename(filetypes=[("SRT files", "*.srt")])
        if self.file_path:
            self.lbl_status_file.config(text=os.path.basename(self.file_path), fg="white")

    def stop_process(self):
        if self.is_running:
            self.is_running = False
            self.log("🛑 STOPPING... Safely aborting.")
            self.btn_stop.config(state="disabled", text="Stopping...")

    def reset_all(self):
        if self.is_running:
            messagebox.showwarning("Warning", "Please STOP first.")
            return
        self.api_var.set(""); self.base_url_var.set(""); self.model_var.set("")
        self.file_path = ""; self.lbl_status_file.config(text="No file selected", fg="#808e9b")
        self.resume_var.set("1"); self.log_box.delete('1.0', tk.END)
        if os.path.exists(CONFIG_FILE): os.remove(CONFIG_FILE)

    def start_process(self):
        if not self.file_path or not self.api_var.get().strip():
            messagebox.showwarning("Input Error", "Provide API Key and File.")
            return
        self.save_settings()
        self.is_running = True
        self.btn_start.config(state="disabled"); self.btn_reset.config(state="disabled"); self.btn_stop.config(state="normal", text="STOP")
        threading.Thread(target=self.translation_thread, daemon=True).start()

    def translation_thread(self):
        try:
            target = self.lang_var.get()
            start_chunk = int(self.resume_var.get())
            if start_chunk < 1: start_chunk = 1
            
            if start_chunk == 1:
                save_path = filedialog.asksaveasfilename(defaultextension=".srt", initialfile=f"Hybrid_{target}.srt")
                if not save_path: raise Exception("Save cancelled")
                open(save_path, 'w', encoding='utf-8').close()
            else:
                save_path = filedialog.askopenfilename(title="Select file to resume", filetypes=[("SRT files", "*.srt")])
                if not save_path: raise Exception("Resume cancelled")

            with open(self.file_path, 'r', encoding='utf-8') as f:
                data = f.read()

            raw_blocks =[b.strip() for b in re.split(r'\n\s*\n', data.strip()) if b.strip()]
            c_size = int(self.chunk_var.get())
            total_chunks = (len(raw_blocks) // c_size) + 1
            
            self.log(f"Hybrid Mode: AI + Google Translate")
            self.log(f"Total Blocks: {len(raw_blocks)} | Chunks: {total_chunks}")

            for i in range((start_chunk-1)*c_size, len(raw_blocks), c_size):
                if not self.is_running: break
                chunk_blocks = raw_blocks[i:i + c_size]
                current_chunk_num = (i//c_size)+1
                
                text_payload = ""
                for j, b in enumerate(chunk_blocks):
                    lines = b.split('\n')
                    text_payload += f"ID_{j}:: {' '.join(lines[2:])}\n"
                
                prompt = f"""Simplify English subtitles.
1. Rewrite into simple plain English. Remove slang.
2. Identify names (people/places). Replace with [N1], [N2].
3. Provide Sinhala transliteration for names.
Output: ID_X::[Simplified Text] ||| [N1]=SinhalaName1
{text_payload}"""
                
                success = False
                while not success and self.is_running:
                    try:
                        self.log(f"⚙️ Chunk {current_chunk_num}: AI Processing...")
                        res_text = ""
                        if self.provider_type == "Gemini":
                            genai.configure(api_key=self.api_var.get().strip())
                            m = genai.GenerativeModel(self.model_var.get().strip())
                            res_text = m.generate_content(prompt).text
                        else:
                            client = OpenAI(api_key=self.api_var.get().strip(), base_url=self.base_url_var.get().strip() if self.base_url_var.get() != "N/A" else None)
                            res_text = client.chat.completions.create(model=self.model_var.get().strip(), messages=[{"role": "user", "content": prompt}]).choices[0].message.content

                        if res_text:
                            self.log(f"🌍 Chunk {current_chunk_num}: Google Translating...")
                            extracted_texts, name_mappings, valid_ids = [], [], []
                            for line in res_text.strip().split('\n'):
                                if "ID_" in line and "::" in line:
                                    id_part, rest = line.split("::", 1)
                                    text_part, names_part = rest.split("|||", 1) if "|||" in rest else (rest, "NONE")
                                    extracted_texts.append(text_part.strip())
                                    valid_ids.append(int(id_part.replace("ID_", "").strip()))
                                    mapping = {}
                                    if "NONE" not in names_part:
                                        for p in names_part.split(','):
                                            if "=" in p: k, v = p.split('=', 1); mapping[k.strip()] = v.strip()
                                    name_mappings.append(mapping)

                            translated_texts = GoogleTranslator(source='en', target='si').translate_batch(extracted_texts)
                            srt_output = ""
                            for j, t_text in enumerate(translated_texts):
                                for tag, name in name_mappings[j].items(): t_text = t_text.replace(tag, name)
                                orig_lines = chunk_blocks[valid_ids[j]].split('\n')
                                srt_output += f"{orig_lines[0]}\n{orig_lines[1]}\n{t_text}\n\n"
                            
                            with open(save_path, 'a', encoding='utf-8') as f: f.write(srt_output)
                            self.log(f"✅ Chunk {current_chunk_num} success!")
                            success = True
                    except Exception as e:
                        self.log(f"⚠️ Error: {str(e)[:40]}... Retrying")
                        time.sleep(15)

                if self.is_running and self.delay_enabled.get() and i + c_size < len(raw_blocks):
                    self.log("⏳ Delaying 15s...")
                    time.sleep(15)

            if self.is_running:
                self.log("🎉 ALL DONE!")
                messagebox.showinfo("Done", "Success!")
        except Exception as e:
            self.log(f"CRITICAL: {str(e)}")
        finally:
            self.is_running = False
            self.btn_start.config(state="normal"); self.btn_reset.config(state="normal"); self.btn_stop.config(state="disabled", text="STOP")

if __name__ == "__main__":
    root = tk.Tk(); app = HybridSubtitleApp(root); root.mainloop()
