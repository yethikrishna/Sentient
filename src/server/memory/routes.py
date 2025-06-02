from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
import traceback
import asyncio # Required for loop.run_in_executor
import datetime # for isoformat and now()
import json # For processing LinkedIn data if it's JSON

# Assuming these are initialized in app.py and can be imported
from server.app.app import (
    auth,
    PermissionChecker,
    mongo_manager, # For load_user_profile
    graph_driver,
    embed_model,
    text_conversion_runnable,
    query_classification_runnable,
    fact_extraction_runnable,
    information_extraction_runnable,
    graph_analysis_runnable,
    graph_decision_runnable,
    text_description_runnable,
    text_dissection_runnable,
    text_summarizer_runnable, # <<<< ADDED: Assuming this is available from app.py
    memory_backend, # Short-term memory manager
    USER_PROFILE_DB_DIR # For input_docs path
)
from server.memory.functions import (
    query_user_profile,
    build_initial_knowledge_graph,
    delete_source_subgraph,
    crud_graph_operations,
    update_neo4j_with_onboarding_data # For onboarding endpoint
)
# from server.memory.helpers import summarize_and_write_sync # We will define this or assume it's defined as above
from server.memory.constants import CATEGORIES # For get-memory-categories
# Pydantic models moved from app.py
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
import os # for os.path.join, os.makedirs

router = APIRouter(
    prefix="/memory",
    tags=["Memory & Knowledge Graph"]
)

# --- Pydantic Models for Memory Endpoints ---
class GraphRAGRequest(BaseModel):
    query: str

class DeleteSubgraphRequest(BaseModel):
    source: str

class GraphRequest(BaseModel):
    information: str

class GetShortTermMemoriesRequest(BaseModel):
    category: str
    limit: int = Field(10, ge=1)

class AddMemoryRequest(BaseModel):
    text: str
    category: str
    retention_days: int = Field(..., ge=1)

class UpdateMemoryRequest(BaseModel):
    id: Any # Can be int or string depending on DB
    text: str
    category: str
    retention_days: int = Field(..., ge=1)

class DeleteMemoryRequest(BaseModel):
    id: Any # Can be int or string
    category: str

# --- Placeholder/Definitions for summarize_and_write_sync dependencies ---
# This should ideally be a constant in server.memory.constants or a similar shared location.
PERSONALITY_DESCRIPTIONS = {
    "introverted": "Prefers solitary activities and gains energy from spending time alone.",
    "extroverted": "Gains energy from social interaction and enjoys being around others.",
    "analytical": "Tends to analyze situations logically and make decisions based on facts.",
    "creative": "Enjoys thinking outside the box and coming up with novel ideas.",
    "organized": "Prefers structure and order, and is good at planning.",
    "ambitious": "Driven to achieve goals and succeed.",
    "curious": "Eager to know or learn something.",
    "empathetic": "Able to understand and share the feelings of another.",
    # Add more as needed from your original PERSONALITY_DESCRIPTIONS
}

# Definition for summarize_and_write_sync
# This function should ideally be in a helpers module, e.g., server.memory.helpers.py
def summarize_and_write_sync(
    username_for_prompt: str,
    text_to_summarize: str,
    output_filename: str,
    base_input_dir: str,
    summarizer_instance: Any  # Instance of your text summarizer runnable
) -> tuple[bool, Optional[str]]:
    """
    Summarizes text and writes it to a file. Runs synchronously.
    Returns (success_status, filename_processed).
    """
    if not text_to_summarize:
        print(f"[{datetime.datetime.now(datetime.timezone.utc)}] [SUMMARIZE_WRITE_SYNC] Skipping empty text for {output_filename}.")
        return False, output_filename

    # print(f"[{datetime.datetime.now(datetime.timezone.utc)}] [SUMMARIZE_WRITE_SYNC] Summarizing content for {output_filename} for user {username_for_prompt}...")
    try:
        # Assuming summarizer_instance.invoke({"user_name": ..., "text": ...})
        summarized_paragraph = summarizer_instance.invoke({
            "user_name": username_for_prompt,
            "text": text_to_summarize
        })
        
        if not summarized_paragraph or not isinstance(summarized_paragraph, str):
            print(f"[{datetime.datetime.now(datetime.timezone.utc)}] [SUMMARIZE_WRITE_SYNC] Summarizer returned empty/invalid content for {output_filename}: {summarized_paragraph}")
            return False, output_filename

        file_path = os.path.join(base_input_dir, output_filename)
        # print(f"[{datetime.datetime.now(datetime.timezone.utc)}] [SUMMARIZE_WRITE_SYNC] Writing summarized content to {file_path}...")
        with open(file_path, "w", encoding="utf-8") as file:
            file.write(summarized_paragraph)
        return True, output_filename
    except Exception as e:
        error_msg = f"Failed to summarize or write file {output_filename}: {e}"
        print(f"[{datetime.datetime.now(datetime.timezone.utc)}] [ERROR_SUMMARIZE_WRITE_SYNC] {error_msg}")
        # traceback.print_exc() is handled by the main endpoint
        return False, output_filename
# --- End of definitions ---


# --- Memory and Knowledge Graph Endpoints ---
@router.post("/graphrag", status_code=status.HTTP_200_OK, summary="Query Knowledge Graph (RAG)")
async def graphrag(request: GraphRAGRequest, user_id: str = Depends(PermissionChecker(required_permissions=["read:memory"]))):
    print(f"[ENDPOINT /memory/graphrag] User {user_id}, Query: '{request.query[:50]}...'")
    try:
        if not all([graph_driver, embed_model, text_conversion_runnable, query_classification_runnable]):
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="GraphRAG dependencies unavailable.")
        # query_user_profile is a synchronous function from server.memory.functions
        context = await asyncio.to_thread(query_user_profile, user_id, request.query, graph_driver, embed_model, text_conversion_runnable, query_classification_runnable)
        return JSONResponse(content={"context": context or "No relevant context found."})
    except Exception as e:
        print(f"[ERROR] /memory/graphrag {user_id}: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="GraphRAG query failed.")

@router.post("/initiate-long-term-memories", status_code=status.HTTP_200_OK, summary="Initialize/Reset Knowledge Graph")
async def create_graph(request_data: Optional[Dict[str, bool]] = None, user_id: str = Depends(PermissionChecker(required_permissions=["write:memory"]))):
    clear_graph_flag = request_data.get("clear_graph", False) if request_data else False
    action = "Resetting/rebuilding" if clear_graph_flag else "Initiating/Updating"
    print(f"[ENDPOINT /memory/initiate-LTM] {action} KG for user {user_id}.")
    loop = asyncio.get_event_loop()
    input_dir = os.path.join(USER_PROFILE_DB_DIR, user_id, "input_docs")
    os.makedirs(input_dir, exist_ok=True)

    try:
        user_profile_doc = await mongo_manager.get_user_profile(user_id) # Use mongo_manager
        username = user_profile_doc.get("userData", {}).get("personalInfo", {}).get("name", user_id) if user_profile_doc else user_id
        if not all([graph_driver, embed_model, text_dissection_runnable, information_extraction_runnable]):
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Graph building dependencies unavailable.")

        def read_files_sync(udir, uid, uname): # This function remains sync
            # Prioritize specific docs if they exist from create_document_route
            doc_priority = [
                f"{uid}_personality_summary.txt", # If we decide to create this one too
                f"{uid}_linkedin_profile.txt",
                f"{uid}_profile_summary.txt", # General summary
            ]
            docs_content = []
            for doc_name in doc_priority:
                fpath = os.path.join(udir, doc_name)
                if os.path.exists(fpath):
                    with open(fpath, "r", encoding="utf-8") as f:
                        docs_content.append({"text": f.read(), "source": os.path.basename(fpath)})
            
            if docs_content:
                return docs_content

            # Fallback to generic profile summary or default if specific docs not found
            fpath = os.path.join(udir, f"{uid}_profile_summary.txt")
            if os.path.exists(fpath):
                with open(fpath, "r", encoding="utf-8") as f:
                    return [{"text": f.read(), "source": os.path.basename(fpath)}]
            return [{"text": f"Initial data for {uname}. Preferences: Likes Italian food. Works as a software engineer.", "source": "default_sample.txt"}]
        
        extracted_texts = await loop.run_in_executor(None, read_files_sync, input_dir, user_id, username)

        if clear_graph_flag:
            print(f"Clearing KG for user: {user_id}...")
            def clear_neo4j_user_graph_sync(driver, uid_scope: str):
                with driver.session(database="neo4j") as session:
                    query = "MATCH (n {userId: $userId_scope}) DETACH DELETE n"
                    session.execute_write(lambda tx: tx.run(query, userId_scope=uid_scope))
            await loop.run_in_executor(None, clear_neo4j_user_graph_sync, graph_driver, user_id)
            print(f"Graph cleared for user: {user_id}.")

        if extracted_texts:
            await loop.run_in_executor(None, build_initial_knowledge_graph, user_id, extracted_texts, graph_driver, embed_model, text_dissection_runnable, information_extraction_runnable) # Pass user_id instead of username for KG operations for consistency
            return JSONResponse(content={"message": f"Knowledge Graph {action.lower()} for user {user_id} completed."})
        else:
            return JSONResponse(content={"message": "No input documents found. Graph not modified."})
    except Exception as e:
        print(f"[ERROR] /memory/initiate-LTM {user_id}: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Knowledge Graph operation failed.")

@router.post("/delete-subgraph", status_code=status.HTTP_200_OK, summary="Delete Subgraph by Source")
async def delete_subgraph_route(request: DeleteSubgraphRequest, user_id: str = Depends(PermissionChecker(required_permissions=["write:memory"]))):
    source_key = request.source.lower().replace(' ', '_')
    print(f"[ENDPOINT /memory/delete-subgraph] User {user_id}, source key: {source_key}")
    loop = asyncio.get_event_loop()
    try:
        # The source identifier should match how it's stored/named, e.g. user_id based
        source_identifier_in_graph = f"{user_id}_{source_key}.txt" 
        # If source is 'linkedin_profile', then source_identifier_in_graph becomes 'user123_linkedin_profile.txt'

        if not graph_driver:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Neo4j driver unavailable.")
        
        await loop.run_in_executor(None, delete_source_subgraph, graph_driver, source_identifier_in_graph, user_id)

        input_dir_path = os.path.join(USER_PROFILE_DB_DIR, user_id, "input_docs")
        file_to_delete_on_disk = os.path.join(input_dir_path, source_identifier_in_graph) # Match the graph ID
        
        def remove_file_sync(path):
            if os.path.exists(path):
                try:
                    os.remove(path)
                    return True, None
                except OSError as e_os:
                    return False, str(e_os)
            return False, "File not found on disk for deletion."
        
        deleted, ferr = await loop.run_in_executor(None, remove_file_sync, file_to_delete_on_disk)
        if not deleted:
            print(f"[WARN] Could not delete source file {file_to_delete_on_disk}: {ferr}")
        
        return JSONResponse(content={"message": f"Subgraph for source '{request.source}' (graph id: {source_identifier_in_graph}) processed for deletion."})
    except Exception as e:
        print(f"[ERROR] /memory/delete-subgraph {user_id}: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Subgraph deletion failed.")

@router.post("/create-document", status_code=status.HTTP_200_OK, summary="Create Input Documents from Profile")
async def create_document_route(user_id: str = Depends(PermissionChecker(required_permissions=["write:profile"]))):
    print(f"[ENDPOINT /memory/create-document] User {user_id}. Timestamp: {datetime.datetime.now(datetime.timezone.utc)}")
    input_dir = os.path.join(USER_PROFILE_DB_DIR, user_id, "input_docs")
    loop = asyncio.get_event_loop()
    
    tasks = []
    created_files_info = []
    failed_files_info = []
    unified_personality_description_text = ""

    try:
        await loop.run_in_executor(None, os.makedirs, input_dir, True) # exist_ok=True

        user_profile_doc = await mongo_manager.get_user_profile(user_id)
        if not user_profile_doc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User profile not found for user_id: {user_id}")
        
        db_user_data = user_profile_doc.get("userData", {})
        username = db_user_data.get("personalInfo", {}).get("name", user_id) # Fallback to user_id if name not present

        if not text_summarizer_runnable:
             raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Text summarizer service is not available.")

        # 1. Process Personality Traits
        personality_data = db_user_data.get("personalityInfo", {}).get("personalityType", [])
        processed_personality_traits = []
        if isinstance(personality_data, str):
            processed_personality_traits = [p.strip().lower() for p in personality_data.split(',') if p.strip()]
        elif isinstance(personality_data, list):
            processed_personality_traits = [str(p).strip().lower() for p in personality_data if str(p).strip()]
        
        trait_descriptions_for_summary = []
        if processed_personality_traits:
            print(f"Processing {len(processed_personality_traits)} personality traits for {user_id}...")
            for trait in processed_personality_traits:
                if trait in PERSONALITY_DESCRIPTIONS:
                    description = f"{trait.capitalize()}: {PERSONALITY_DESCRIPTIONS[trait]}"
                    trait_descriptions_for_summary.append(description)
                    filename = f"{user_id}_{trait}.txt" # Use user_id for filename consistency
                    tasks.append(loop.run_in_executor(
                        None, summarize_and_write_sync, username, description, filename, input_dir, text_summarizer_runnable
                    ))
                else:
                    print(f"[WARN] Personality trait '{trait}' not found in PERSONALITY_DESCRIPTIONS for user {user_id}. Skipping.")
            if trait_descriptions_for_summary:
                unified_personality_description_text = f"{username}'s Personality Traits:\n\n" + "\n".join(trait_descriptions_for_summary)
                # Optionally, save this unified summary as its own document
                # unified_filename = f"{user_id}_personality_summary.txt"
                # tasks.append(loop.run_in_executor(None, summarize_and_write_sync, username, unified_personality_description_text, unified_filename, input_dir, text_summarizer_runnable))


        # 2. Process LinkedIn Profile
        # Adjust key based on your actual profile structure, e.g., "professionalInfo.linkedInSummary" or "professionalInfo.linkedInProfile"
        linkedin_profile_data = db_user_data.get("professionalInfo", {}).get("linkedInProfileSummary") # Example key
        if not linkedin_profile_data: # Try another common key pattern
            linkedin_profile_data = db_user_data.get("linkedInProfile")

        if linkedin_profile_data:
            print(f"Processing LinkedIn profile for {user_id}...")
            linkedin_text = ""
            if isinstance(linkedin_profile_data, dict):
                # You might want a more sophisticated way to convert dict to text
                linkedin_text = json.dumps(linkedin_profile_data, indent=2) 
            elif isinstance(linkedin_profile_data, str):
                linkedin_text = linkedin_profile_data
            
            if linkedin_text:
                linkedin_file = f"{user_id}_linkedin_profile.txt"
                tasks.append(loop.run_in_executor(
                    None, summarize_and_write_sync, username, linkedin_text, linkedin_file, input_dir, text_summarizer_runnable
                ))
        else:
            print(f"No LinkedIn profile data found for user {user_id}.")

        # Helper to process social media interests
        def process_social_media(data_key_path: list, source_name: str):
            current_level = db_user_data
            for key in data_key_path:
                current_level = current_level.get(key, {})
            
            social_data = current_level # This should be the list or string
            
            processed_social_topics = []
            if isinstance(social_data, str):
                processed_social_topics = [topic.strip() for topic in social_data.split(',') if topic.strip()]
            elif isinstance(social_data, list):
                processed_social_topics = [str(topic).strip() for topic in social_data if str(topic).strip()]

            if processed_social_topics:
                print(f"Processing {source_name} profile for {user_id}...")
                social_text = f"User {username}'s {source_name} Interests: " + ", ".join(processed_social_topics)
                social_file = f"{user_id}_{source_name.lower()}_profile.txt"
                tasks.append(loop.run_in_executor(
                    None, summarize_and_write_sync, username, social_text, social_file, input_dir, text_summarizer_runnable
                ))
            else:
                print(f"No {source_name} profile data found for user {user_id}.")

        # 3. Process Reddit Profile (Example path: userData.socialMedia.redditInterests)
        process_social_media(["socialMedia", "redditInterests"], "Reddit")
        
        # 4. Process Twitter Profile (Example path: userData.socialMedia.twitterInterests)
        process_social_media(["socialMedia", "twitterInterests"], "Twitter")


        # --- General Profile Summary (Optional - can be redundant if specific parts are well-covered) ---
        # The previous version created a single summary. If you still want a general one:
        general_summary_parts = []
        # Example: take top-level non-dict items or specific important fields
        for key, value in db_user_data.get("personalInfo", {}).items():
            if not isinstance(value, (dict, list)): general_summary_parts.append(f"{key.replace('_', ' ').title()}: {value}")
        for key, value in db_user_data.get("preferences", {}).items(): # Example: userData.preferences
             if not isinstance(value, (dict, list)): general_summary_parts.append(f"Preference - {key.replace('_', ' ').title()}: {value}")

        if general_summary_parts:
            general_summary_text = f"General Profile Information for {username}:\n" + "\n".join(general_summary_parts)
            general_summary_filename = f"{user_id}_profile_summary.txt" # Generic summary
            tasks.append(loop.run_in_executor(None, summarize_and_write_sync, username, general_summary_text, general_summary_filename, input_dir, text_summarizer_runnable))


        # Wait for all summarize/write tasks to complete
        if tasks:
            print(f"Waiting for {len(tasks)} summarization/write tasks to complete for user {user_id}...")
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for result in results:
                if isinstance(result, Exception):
                    print(f"[ERROR] Task failed in asyncio.gather: {result}")
                    # Decide how to handle: perhaps add to failed_files_info with a generic error
                    failed_files_info.append(f"Unknown file due to task error: {type(result).__name__}")
                elif isinstance(result, tuple) and len(result) == 2:
                    success, filename = result
                    if success and filename:
                        created_files_info.append(filename)
                    elif filename: # Failed but filename is known
                        failed_files_info.append(filename)
                else:
                    print(f"[WARN] Unexpected result from task: {result}")


        print(f"Document creation process finished for user {user_id}.")
        print(f"Successfully created {len(created_files_info)} files: {created_files_info}")
        if failed_files_info:
            print(f"Failed to create/summarize {len(failed_files_info)} files: {failed_files_info}")

        return JSONResponse(content={
            "message": f"Documents processed for user {user_id}. Created: {len(created_files_info)}, Failed: {len(failed_files_info)}.",
            "created_files": created_files_info,
            "failed_files": failed_files_info,
            "personality_summary_text": unified_personality_description_text # Return the combined description
        })

    except HTTPException as he: # Re-raise HTTPExceptions
        raise he
    except Exception as e:
        print(f"[ERROR] /memory/create-document {user_id}: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Document creation failed: {str(e)}")


@router.post("/customize-long-term-memories", status_code=status.HTTP_200_OK, summary="Customize KG with Text")
async def customize_graph(request: GraphRequest, user_id: str = Depends(PermissionChecker(required_permissions=["write:memory"]))):
    print(f"[ENDPOINT /memory/customize-LTM] User {user_id}, Info: '{request.information[:50]}...'")
    loop = asyncio.get_event_loop()
    try:
        user_profile_doc = await mongo_manager.get_user_profile(user_id)
        username = user_profile_doc.get("userData", {}).get("personalInfo", {}).get("name", user_id) if user_profile_doc else user_id
        required_deps = [graph_driver, embed_model, fact_extraction_runnable, query_classification_runnable, information_extraction_runnable, graph_analysis_runnable, graph_decision_runnable, text_description_runnable]
        if not all(required_deps):
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Graph customization dependencies unavailable.")

        # Make sure the input to fact_extraction_runnable is what it expects
        fact_input = {"paragraph": request.information}
        if "username" in fact_extraction_runnable.input_schema.schema().get("properties", {}): # Check if username is an expected key
            fact_input["username"] = username
            
        extracted_points_data = await loop.run_in_executor(None, fact_extraction_runnable.invoke, fact_input)
        
        extracted_points = []
        if isinstance(extracted_points_data, dict) and "facts" in extracted_points_data and isinstance(extracted_points_data["facts"], list):
            extracted_points = extracted_points_data["facts"]
        elif isinstance(extracted_points_data, list): # If the runnable directly returns a list of facts
            extracted_points = extracted_points_data
        else:
            print(f"[WARN] Unexpected format from fact_extraction_runnable for user {user_id}: {type(extracted_points_data)}, data: {str(extracted_points_data)[:200]}")
            # Attempt to adapt if it's a string that might be a list of facts or similar common mistake
            if isinstance(extracted_points_data, str) and extracted_points_data.strip().startswith("[") and extracted_points_data.strip().endswith("]"):
                try:
                    extracted_points = json.loads(extracted_points_data)
                    if not isinstance(extracted_points, list): extracted_points = [] # reset if not a list
                except json.JSONDecodeError:
                    print(f"[WARN] Could not parse string from fact_extraction_runnable as JSON list for user {user_id}")
                    extracted_points = [extracted_points_data] # Treat the whole string as one point if parsing fails but it's a string
            elif isinstance(extracted_points_data, str): # Treat as single fact if it's just a string.
                 extracted_points = [extracted_points_data]


        if not extracted_points:
            return JSONResponse(content={"message": "No facts extracted or facts format unrecognized. Graph not modified."})

        crud_tasks = [loop.run_in_executor(None, crud_graph_operations, user_id, point, graph_driver, embed_model, query_classification_runnable, information_extraction_runnable, graph_analysis_runnable, graph_decision_runnable, text_description_runnable) for point in extracted_points]
        crud_results = await asyncio.gather(*crud_tasks, return_exceptions=True)
        
        processed_count = sum(1 for r in crud_results if not isinstance(r, Exception) and r is not None) # Assuming crud_graph_operations returns non-None on success
        error_results = [str(r) for r in crud_results if isinstance(r, Exception)]
        
        msg = f"Knowledge Graph customization processed {processed_count}/{len(extracted_points)} facts for user {user_id}."
        if error_results:
            msg += f" Errors encountered with {len(error_results)} facts."
        
        return JSONResponse(status_code=status.HTTP_200_OK if not error_results else status.HTTP_207_MULTI_STATUS, content={"message": msg, "errors": error_results if error_results else []})
    except Exception as e:
        print(f"[ERROR] /memory/customize-LTM {user_id}: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Knowledge Graph customization failed.")


# --- Short-Term Memory Endpoints ---
@router.post("/get-short-term-memories", status_code=status.HTTP_200_OK, summary="Get Short-Term Memories")
async def get_short_term_memories(request: GetShortTermMemoriesRequest, user_id: str = Depends(PermissionChecker(required_permissions=["read:memory"]))):
    print(f"[ENDPOINT /memory/get-STM] User {user_id}, Cat: {request.category}, Lim: {request.limit}")
    try:
        memories = await memory_backend.memory_manager.fetch_memories_by_category(user_id, request.category, request.limit) # fetch_memories_by_category is already async
        s_mem = []
        for m in memories:
            # Ensure datetime objects are converted to ISO format strings
            if 'created_at' in m and isinstance(m['created_at'], datetime.datetime):
                m['created_at'] = m['created_at'].isoformat()
            if 'expiry_at' in m and isinstance(m['expiry_at'], datetime.datetime): 
                m['expiry_at'] = m['expiry_at'].isoformat()
            s_mem.append(m)
        return JSONResponse(content=s_mem)
    except Exception as e:
        print(f"[ERROR] /memory/get-STM {user_id}: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to fetch short-term memories.")

@router.post("/add-short-term-memory", status_code=status.HTTP_201_CREATED, summary="Add STM")
async def add_memory(request: AddMemoryRequest, user_id: str = Depends(PermissionChecker(required_permissions=["write:memory"]))):
    print(f"[ENDPOINT /memory/add-STM] User {user_id}, Cat: {request.category}")
    try:
        # store_memory in MemoryManager is async
        mem_id = await memory_backend.memory_manager.store_memory(user_id, request.text, request.retention_days, request.category)
        return JSONResponse(content={"memory_id": str(mem_id), "message": "Short-term memory added."}, status_code=status.HTTP_201_CREATED) # Ensure mem_id is string
    except Exception as e:
        print(f"[ERROR] /memory/add-STM {user_id}: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to add short-term memory.")

@router.post("/update-short-term-memory", status_code=status.HTTP_200_OK, summary="Update STM")
async def update_memory_route(request: UpdateMemoryRequest, user_id: str = Depends(PermissionChecker(required_permissions=["write:memory"]))):
    print(f"[ENDPOINT /memory/update-STM] User {user_id}, ID: {request.id}")
    try:
        # update_memory_crud in MemoryManager is async
        await memory_backend.memory_manager.update_memory_crud(user_id, request.category, request.id, request.text, request.retention_days)
        return JSONResponse(content={"message": "Short-term memory updated."})
    except ValueError as ve: # Catch specific "Memory not found" errors
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))
    except Exception as e:
        print(f"[ERROR] /memory/update-STM {user_id}: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update short-term memory.")

@router.post("/delete-short-term-memory", status_code=status.HTTP_200_OK, summary="Delete STM")
async def delete_memory_route(request: DeleteMemoryRequest, user_id: str = Depends(PermissionChecker(required_permissions=["write:memory"]))):
    print(f"[ENDPOINT /memory/delete-STM] User {user_id}, ID: {request.id}, Cat: {request.category}")
    try:
        # delete_memory in MemoryManager is async
        await memory_backend.memory_manager.delete_memory(user_id, request.category, request.id)
        return JSONResponse(content={"message": "Short-term memory deleted."})
    except ValueError as ve: # Catch specific "Memory not found" errors
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))
    except Exception as e:
        print(f"[ERROR] /memory/delete-STM {user_id}: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to delete short-term memory.")

@router.post("/clear-all-short-term-memories", status_code=status.HTTP_200_OK, summary="Clear All STM")
async def clear_all_memories(user_id: str = Depends(PermissionChecker(required_permissions=["write:memory"]))):
    print(f"[ENDPOINT /memory/clear-all-STM] User {user_id}.")
    try:
        # clear_all_memories in MemoryManager is async
        await memory_backend.memory_manager.clear_all_memories(user_id)
        return JSONResponse(content={"message": "All short-term memories cleared."})
    except Exception as e:
        print(f"[ERROR] /memory/clear-all-STM {user_id}: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to clear all short-term memories.")

@router.post("/get-memory-categories", status_code=status.HTTP_200_OK, summary="Get Memory Categories")
async def get_memory_categories_route(user_id: str = Depends(PermissionChecker(required_permissions=["read:memory"]))): # Added _route suffix to avoid conflict
    print(f"[ENDPOINT /memory/get-memory-categories] User {user_id}.")
    try:
        # Ensure CATEGORIES is a list or dict that can be JSON serialized
        if isinstance(CATEGORIES, (list, dict)):
            return JSONResponse(content={"categories": CATEGORIES})
        else:
            # If CATEGORIES is some other type (e.g. Enum), convert appropriately
            # This is a fallback, ideally CATEGORIES is already in a serializable format
            try:
                # Attempt to convert if it's an Enum or similar iterable
                return JSONResponse(content={"categories": [c.value if hasattr(c, 'value') else str(c) for c in CATEGORIES]})
            except TypeError:
                 return JSONResponse(content={"categories": str(CATEGORIES)}) # Last resort
    except Exception as e:
        print(f"[ERROR] /memory/get-memory-categories {user_id}: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve memory categories.")


@router.post("/get-graph-data", status_code=status.HTTP_200_OK, summary="Get KG Data (Visualization)")
async def get_graph_data_apoc(user_id: str = Depends(PermissionChecker(required_permissions=["read:memory"]))):
    print(f"[ENDPOINT /memory/get-graph-data] User {user_id}.")
    loop = asyncio.get_event_loop()
    if not graph_driver:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Neo4j driver unavailable.")
    
    # Updated query to ensure it only pulls nodes/rels related to the specific user
    # It also ensures that relationships shown are between user-specific nodes.
    graph_visualization_query = """
    MATCH (n) WHERE n.userId = $userId
    OPTIONAL MATCH (n)-[r]-(m) WHERE m.userId = $userId
    WITH collect(DISTINCT n) + collect(DISTINCT m) as all_nodes_collection, collect(DISTINCT r) as rels_list
    UNWIND all_nodes_collection as distinct_node // Unwind to get distinct nodes
    WITH collect(DISTINCT distinct_node) as nodes_list_distinct, rels_list
    RETURN 
        [node IN nodes_list_distinct | 
            { 
                id: elementId(node), 
                label: coalesce(labels(node)[0], 'UnknownNode'), 
                properties: properties(node) 
            }
        ] AS nodes,
        [rel_item IN rels_list WHERE rel_item IS NOT NULL | 
            { 
                id: elementId(rel_item), 
                from: elementId(startNode(rel_item)), 
                to: elementId(endNode(rel_item)), 
                label: type(rel_item), 
                properties: properties(rel_item) 
            }
        ] AS edges
    """

    def run_q(driver, query, params):
        with driver.session(database="neo4j") as session:
            res = session.run(query, params).single() # Expect a single row
            if res:
                return (res.get('nodes', []), res.get('edges', []))
            return ([], []) # Return empty lists if no result
            
    try:
        nodes, edges = await loop.run_in_executor(None, run_q, graph_driver, graph_visualization_query, {"userId": user_id})
        return JSONResponse(content={"nodes": nodes, "edges": edges})
    except Exception as e:
        print(f"[ERROR] /memory/get-graph-data {user_id}: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to get graph data.")