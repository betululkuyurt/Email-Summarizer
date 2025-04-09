import json
import google.generativeai as genai

from src.llm.output_structures import CategorizedEvents, ListOfSylabusEvents
from src.util.display_helpers import display_events, extract_text_from_file, get_unique_categories
from src.llm.system_instructions import extractor_agent_system_instruction, extractor_agent_tester_system_instruction, syllabus_agent_system_instruction
from markdown import markdown as md

# Global token usage tracker
token_usage_tracker = {
    "input_tokens": 0,
    "output_tokens": 0,
    "total_tokens": 0
}


class Agent:
    def __init__(self, name, role, model_code, output_schema, temperature, top_p, top_k):
        self.name = name
        self.role = role
        self.model = genai.GenerativeModel(model_code,
                                           system_instruction=role, generation_config=genai.GenerationConfig(
        response_mime_type="application/json", response_schema=list[output_schema], temperature=temperature, top_p=top_p, top_k=top_k
    ))

    def generate_response(self, prompt):
        # Track input tokens
        input_token_count = len(prompt.split())  # Simplified token count approximation
        token_usage_tracker["input_tokens"] += input_token_count

        response = self.model.generate_content(prompt)

        # Track output tokens
        output_token_count = len(response.text.split())  # Simplified token count approximation
        token_usage_tracker["output_tokens"] += output_token_count

        # Update total token usage
        token_usage_tracker["total_tokens"] += input_token_count + output_token_count

        # Log token usage in the terminal
        print(f"Agent: {self.name}")
        print(f"Input Tokens: {input_token_count}")
        print(f"Output Tokens: {output_token_count}")
        print(f"Total Tokens So Far: {token_usage_tracker['total_tokens']}")

        return response

# Function to display token usage summary
def display_token_usage():
    return (f"Input Tokens: {token_usage_tracker['input_tokens']}, "
            f"Output Tokens: {token_usage_tracker['output_tokens']}, "
            f"Total Tokens: {token_usage_tracker['total_tokens']}")


    
def configure_gemini(API_KEY): 
    # Gemini Configuration
    genai.configure(api_key=API_KEY)


def summarize_inbox(messages): 
    """Fetch and summarize the user's inbox with a structured JSON output."""
    try:      
        # Prepare the content for summarization
        inbox_text = "\n---\n".join([
            f"From: {msg['from']}\nReceived: {msg['receivedDateTime']}\nSubject: {msg['subject']}\nBody: {md(msg['body'])}"
            for msg in messages
        ])
        
        # Use Gemini model for text generation
        agent = Agent("EventExtractorAgent", extractor_agent_system_instruction, "gemini-1.5-flash", CategorizedEvents, 0.3, 0.9, 40)
        # Use Gemini model for testing the output
        tester_agent = Agent("Revision Specialist Agent", extractor_agent_tester_system_instruction, "gemini-1.5-flash", CategorizedEvents, 0.3, 0.9, 40)

        # Generate the summary
        response = agent.generate_response(inbox_text)

        # Try to parse and validate the JSON
        try:
        
            response_text = response.text # Initialize response text, if JSON parsing fails, this will be used
 
            if "json" in response.text:
                response_text = response.text.split("json")[1].split("```")[0].strip()

            # Send the response to the tester agent for validation
            tester_agent_response = tester_agent.generate_response("Start of the Emails: " + inbox_text + "\n ----------- End of the Emails ---------------- \n ExtractorAgent's Output on Emails:" + str(response_text))
           
            tester_response_json = json.loads(tester_agent_response.text) #Parse the response from the tester agent
            
            print(tester_response_json)
            # Log token usage summary to terminal
            print("Token Usage Summary:")
            print(display_token_usage())

            # Return both the categorized events and unique categories
            return {
                'events': tester_response_json,
                'categories': get_unique_categories(tester_response_json)
                
            }
        
        except json.JSONDecodeError:
            # If JSON parsing fails, return an error response
            return {
                'error': "Failed to parse summary as JSON",
                'raw_response': response.text
            }
    
    except Exception as e:
        print("Error during summarization:", str(e))
        print("Token Usage Summary:")
        print(display_token_usage())
        return {'error': f"Error during summarization: {str(e)}"}
    


def process_syllabus_text(syllabus_agent, syllabus_text):
    """
    Analyze the syllabus text for structured information.
    """
    try:
        response = syllabus_agent.generate_response(syllabus_text)
        response_text = response.content if hasattr(response, 'content') else response.text

        # Parse and return the structured JSON response
        return json.loads(response_text)
    except json.JSONDecodeError as e:
        return {"error": f"Failed to parse syllabus analysis: {str(e)}"}
    except Exception as e:
        return {"error": f"An error occurred: {str(e)}"}
      
                
            
    except Exception as e:
        return f"Error processing syllabus: {str(e)}"
    
def generate_html_table(events):
    """
    Generate an HTML table from a list of event dictionaries.
    """
    # Start table HTML
    html = """
    <table border="1">
        <thead>
            <tr>
                <th>Course Code</th>
                <th>Event Name</th>
                <th>Event Week No / Date</th>
                <th>Category</th>
            </tr>
        </thead>
        <tbody>
    """
    # Add rows for each event
    for event in events:
        html += f"""
            <tr>
                <td>{event['course_code']}</td>
                <td>{event['event_name']}</td>
                <td>{event['week_info']}</td>
                <td>{event['category']}</td>
            </tr>
        """
    
    # Close table HTML
    html += """
        </tbody>
    </table>
    """
    return html

# New function to handle multiple syllabus files
def process_multiple_syllabus_files(file_paths):
    """
    Process multiple syllabus files and generate HTML tables for each.
    """
    try:
        html_output = ""  # Collect all HTML tables in this string
        
        for file_path in file_paths:  # Iterate over all uploaded files
            syllabus_text = extract_text_from_file(file_path)  # Extract text
            syllabus_agent = Agent(
                "SyllabusAnalyzer", 
                syllabus_agent_system_instruction, 
                "gemini-1.5-flash", 
                ListOfSylabusEvents, 
                0.3, 
                0.8, 
                30
            )
            # Analyze the syllabus text
            summary_result = process_syllabus_text(syllabus_agent, syllabus_text)
            
            if "error" in summary_result:
                html_output += f"<p>Error analyzing file {file_path}: {summary_result['error']}</p>"
                continue
            
            # Generate and append the HTML table for this syllabus
            html_output += f"<h3>Syllabus Analysis for {file_path.split('/')[-1]}</h3>"
            html_output += generate_html_table(summary_result[0]['events'])

        return html_output  # Return the combined HTML output
    
    except Exception as e:
        return f"<p>Error processing syllabi: {str(e)}</p>"