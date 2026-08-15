# (ඉහත කේතයේ ඇති කොටස මෙම කොටසින් ප්‍රතිස්ථාපනය කරන්න)

    elif nav_mode == "📊 Subject Progress & Stats":
        st.markdown(f'''
            <div class="dashboard-header">
                <h1 class="dashboard-title">📊 Subject Progress & Stats ({cfg["selected_year"]} - {cfg["selected_semester"]})</h1>
                <p style="color: #94a3b8; margin: 4px 0 0 0; font-size: 14px;">Detailed progress, cuts/absences, and safe attendance margins for your main subjects.</p>
            </div>
        ''', unsafe_allow_html=True)

        # සියලුම subjects ලබාගෙන ඒවායින් Tutorial නොවන (Main) ඒවා පමණක් පෙරීම
        all_subjects_raw = sorted(list(set(l["subject"] for day in sem_data.get("timetable", {}) for l in sem_data["timetable"][day])))
        main_subjects = [subj for subj in all_subjects_raw if not is_tutorial_subject(subj)]
        
        if not main_subjects:
            st.info("No main subjects found in the timetable for this semester.")
        else:
            for subj in main_subjects:
                # Stats ගණනය කිරීම (tutorial subjects ගණනය කිරීම්වලට බලපාන්නේ නැත)
                s_stat = calculate_subject_stats(subj, cfg, st.session_state['absent_records'])
                
                pct = s_stat['percentage']
                is_at_risk = pct < 80.0
                status_badge = f'<div style="background: rgba(244, 63, 94, 0.15); color: #fb7185; border: 1px solid rgba(244, 63, 94, 0.35); padding: 6px 14px; border-radius: 20px; font-size: 12px; font-weight: 700;">At Risk ({pct:.1f}%)</div>' if is_at_risk else f'<div style="background: rgba(16, 185, 129, 0.15); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.35); padding: 6px 14px; border-radius: 20px; font-size: 12px; font-weight: 700;">Good ({pct:.1f}%)</div>'

                st.markdown(f'''
                    <div class="tracker-card">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 18px;">
                            <h2 style="margin: 0; font-size: 22px; color: #f8fafc; font-weight: 700;">{subj}</h2>
                            {status_badge}
                        </div>
                ''', unsafe_allow_html=True)

                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f'''
                        <div class="stat-box">
                            <div style="font-size: 11px; color: #94a3b8; text-transform: uppercase; font-weight: 700; margin-bottom: 4px;">Conducted</div>
                            <div style="font-size: 22px; font-weight: 800; color: #f8fafc;">{s_stat["past_conducted"]} / {s_stat["total"]}</div>
                        </div>
                    ''', unsafe_allow_html=True)
                with col2:
                    st.markdown(f'''
                        <div class="stat-box">
                            <div style="font-size: 11px; color: #94a3b8; text-transform: uppercase; font-weight: 700; margin-bottom: 4px;">Cuts / Absences</div>
                            <div style="font-size: 22px; font-weight: 800; color: #fb7185;">{s_stat["absences"]}</div>
                        </div>
                    ''', unsafe_allow_html=True)

                # ... ඉතිරි කොටස පෙර පරිදිම පවතී ...
                col3, col4 = st.columns(2)
                with col3:
                    st.markdown(f'''
                        <div class="stat-box">
                            <div style="font-size: 11px; color: #94a3b8; text-transform: uppercase; font-weight: 700; margin-bottom: 4px;">Max Allowed Cuts</div>
                            <div style="font-size: 22px; font-weight: 800; color: #f8fafc;">{s_stat["max_allowed"]}</div>
                        </div>
                    ''', unsafe_allow_html=True)
                with col4:
                    st.markdown(f'''
                        <div class="stat-box">
                            <div style="font-size: 11px; color: #94a3b8; text-transform: uppercase; font-weight: 700; margin-bottom: 4px;">Total Semester</div>
                            <div style="font-size: 22px; font-weight: 800; color: #f8fafc;">{s_stat["total"]}</div>
                        </div>
                    ''', unsafe_allow_html=True)

                safe_left_val = s_stat["safe_left"]
                st.markdown(f'''
                    <div style="background: rgba(16, 185, 129, 0.08); border: 1px solid rgba(16, 185, 129, 0.25); border-radius: 14px; padding: 14px 18px; margin-bottom: 16px; color: #34d399; font-weight: 600; font-size: 14px;">
                        🟢 Safe to miss {safe_left_val} more lecture(s).
                    </div>
                ''', unsafe_allow_html=True)

                if st.button(f"🔍 View History / Manage Absences", key=f"btn_hist_{subj}", use_container_width=True):
                    open_subject_modal(subj, cfg, username)

                st.markdown('</div>', unsafe_allow_html=True)
