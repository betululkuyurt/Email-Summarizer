from src.graphapi.my_msgraph import add_events_to_calendar, authenticate, fetch_inbox, get_access_token
from src.llm.gemini import configure_gemini, process_multiple_syllabus_files, summarize_inbox
from src.util.display_helpers import display_events
import gradio as gr

def create_ui():
    with gr.Blocks() as app:
        # Step 1: Authentication
        with gr.Row(visible=True) as step1:
            with gr.Column():
                gr.Markdown("# Login")
                username_input = gr.Textbox(label="Username", placeholder="Enter your email address")
                password_input = gr.Textbox(label="Password", type="password", placeholder="Enter your password")
                auth_output = gr.Textbox(label="Authentication Status", interactive=False)
                auth_button = gr.Button("Authenticate")
                next_to_step2 = gr.Button("Next")

        # Step 2: Inbox Summary
        with gr.Column(visible=False) as step2:
            with gr.Row():
                with gr.Column():
                    gr.Markdown("# Fetch, Extract and Categorize Events")
                    category_dropdown = gr.Dropdown(label="Filter Events by Category", choices=['All'], interactive=True)
                    summarize_output = gr.HTML(label="Inbox Summary")
                    summarize_button = gr.Button("Summarize Inbox")

                    back_to_step1 = gr.Button("Back to Login")

            # Step 3: Add Events to Calendar
            with gr.Row():
                with gr.Column():
                    gr.Markdown("# Add Events to Calendar (Optional)")
                    add_output = gr.HTML(label="Event Addition Status")
                    add_button = gr.Button("Add Events to Calendar")
            next_to_syllabus = gr.Button("Syllabus Analysis")


         # Syllabus file upload and analysis
        with gr.Row(visible=False) as syllabus_analysis:
            with gr.Column():
                gr.Markdown("# Syllabus Analysis")
                syllabus_file_input = gr.File(
                    label="Upload Syllabus Files (Word or PDF)", 
                    type="filepath", 
                    file_types=[".pdf", ".docx", ".doc"], 
                    file_count="multiple"
                )
                syllabus_output = gr.HTML(label="Syllabus Analysis")
                syllabus_button = gr.Button("Analyze Syllabus")
                back_to_step2 = gr.Button("Back to Inbox Summary")

       
        

        # State variables to hold data
        summary_state = gr.State(None)  # Store all events
        filtered_state = gr.State(None)  # Store filtered events

        # Authentication process
        auth_button.click(
            authenticate,
            inputs=[username_input, password_input],
            outputs=auth_output
        )

        # Summarize inbox and populate categories
        def summarize_and_populate_categories(username, password):
            token = get_access_token(username, password)
            emails = fetch_inbox(token, 50)
            summary_result = summarize_inbox(emails)
            
            if 'events' in summary_result:
                return {
                    summarize_output: display_events(summary_result['events']),
                    category_dropdown: gr.Dropdown(choices=summary_result['categories']),
                    summary_state: summary_result['events']
                }
            elif 'error' in summary_result:
                return {
                    summarize_output: f"<p>Error: {summary_result['error']}</p>",
                    category_dropdown: gr.Dropdown(choices=['All'])
                }

        summarize_button.click(
            summarize_and_populate_categories,
            inputs=[username_input, password_input],
            outputs=[summarize_output, category_dropdown, summary_state]
        )

        # Filter events by category
        def filter_events(summary_events, category):
            if not summary_events:
                return "<p>No events to filter. Please summarize inbox first.</p>", None
            
            filtered_events = [
                event for event in summary_events if category == 'All' or event['category'] == category
            ]
            return display_events(filtered_events), filtered_events

        category_dropdown.change(
            filter_events,
            inputs=[summary_state, category_dropdown],
            outputs=[summarize_output, filtered_state]
        )

        # Add filtered events to calendar
        add_button.click(
            add_events_to_calendar,
            inputs=[filtered_state, username_input, password_input],
            outputs=add_output
        )
        syllabus_button.click(
            process_multiple_syllabus_files,
            inputs=syllabus_file_input,
            outputs=syllabus_output
        )

        # Navigation logic
        next_to_step2.click(lambda: (gr.update(visible=False), gr.update(visible=True)), 
                            inputs=None, outputs=[step1, step2])
        back_to_step1.click(lambda: (gr.update(visible=True), gr.update(visible=False)), 
                            inputs=None, outputs=[step1, step2])
        next_to_syllabus.click(lambda: (gr.update(visible=False), gr.update(visible=True)),
                            inputs=None, outputs=[step2, syllabus_analysis])
        back_to_step2.click(lambda: (gr.update(visible=True), gr.update(visible=False)),
                            inputs=None, outputs=[step2, syllabus_analysis])
   

    return app

configure_gemini("AIzaSyByD_fqtgEnGOKJLjfUc5xikVzKNiZF7K8")
ui = create_ui()
ui.launch()
