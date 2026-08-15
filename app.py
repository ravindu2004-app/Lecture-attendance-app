elif nav_mode == "🚫 Cancel / Extra Lectures":
        st.markdown(f'''
            <div class="dashboard-header">
                <h1 class="dashboard-title">🛠️ Manage Cancelled & Extra Lectures</h1>
                <p style="color: #94a3b8; margin: 4px 0 0 0; font-size: 14px;">Adjust scheduled lectures or add special make-up classes below.</p>
            </div>
        ''', unsafe_allow_html=True)
        
        tab_cancel, tab_extra = st.tabs(["🚫 Cancelled Lectures", "➕ Extra Lectures"])
        all_subjects = sorted(list(set(l["subject"] for day in sem_data.get("timetable", {}) for l in sem_data["timetable"][day])))

        # --- 1. CANCELLED LECTURES SECTION ---
        with tab_cancel:
            st.subheader("Add Cancellation")
            c_date = st.date_input("Select Date to Cancel:", min_value=sem_data.get("start_date"), key="c_date_add")
            day_lectures = sem_data["timetable"].get(c_date.strftime("%A"), [])
            day_subjects = sorted(list(set(l["subject"] for l in day_lectures)))
            
            c_subj = st.selectbox("Select Subject:", options=day_subjects if day_subjects else ["No lectures on this day"], key="c_subj_add")
            
            if st.button("🚫 Mark as Cancelled", type="primary") and day_subjects:
                c_date_str = c_date.strftime("%Y-%m-%d")
                if not any(c["subject"] == c_subj and c["date"] == c_date_str for c in cfg.get("cancelled_lectures", [])):
                    cfg.setdefault("cancelled_lectures", []).append({"subject": c_subj, "date": c_date_str})
                    save_user_config_db(username, cfg)
                    st.rerun()

            st.markdown("---")
            st.subheader("Your Cancelled List")
            cancelled_list = cfg.get("cancelled_lectures", [])
            if not cancelled_list:
                st.info("No cancelled lectures yet.")
            else:
                for idx, item in enumerate(cancelled_list):
                    col_info, col_btn = st.columns([4, 1])
                    col_info.write(f"❌ **{item['subject']}** - `{item['date']}`")
                    if col_btn.button("🗑️", key=f"del_can_{idx}"):
                        cancelled_list.pop(idx)
                        save_user_config_db(username, cfg)
                        st.rerun()

        # --- 2. EXTRA LECTURES SECTION ---
        with tab_extra:
            st.subheader("Add Extra Lecture")
            e_subj = st.selectbox("Select Subject:", options=all_subjects, key="e_subj_add")
            e_date = st.date_input("Select Date:", min_value=sem_data.get("start_date"), key="e_date_add")
            e_st = mobile_time_picker("Start Time", key_prefix="e_st_add")
            e_et = mobile_time_picker("End Time", key_prefix="e_et_add")

            if st.button("➕ Add Extra Class", type="primary"):
                cfg.setdefault("extra_lectures", []).append({
                    "year": cfg["selected_year"], "semester": cfg["selected_semester"],
                    "subject": e_subj, "date": e_date.strftime("%Y-%m-%d"),
                    "start_time": e_st, "end_time": e_et
                })
                save_user_config_db(username, cfg)
                st.rerun()

            st.markdown("---")
            st.subheader("Your Extra Classes")
            extra_list = cfg.get("extra_lectures", [])
            # Filter කරන්නේ දැනට තෝරාගෙන ඇති Year/Sem එකට අදාළ ඒවා පමණක් පෙන්වන්න
            current_extras = [ex for ex in extra_list if ex.get("year") == cfg["selected_year"] and ex.get("semester") == cfg["selected_semester"]]
            
            if not current_extras:
                st.info("No extra lectures added.")
            else:
                for idx, item in enumerate(current_extras):
                    col_info, col_btn = st.columns([4, 1])
                    col_info.write(f"✨ **{item['subject']}** - `{item['date']}` ({item['start_time']} - {item['end_time']})")
                    if col_btn.button("🗑️", key=f"del_ext_{idx}"):
                        # මුල් list එකෙන් අදාළ item එක ඉවත් කිරීම
                        extra_list.remove(item)
                        save_user_config_db(username, cfg)
                        st.rerun()
