--
-- PostgreSQL database dump
--

-- Dumped from database version 15.13
-- Dumped by pg_dump version 15.13

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: vector; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public;


--
-- Name: EXTENSION vector; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION vector IS 'vector data type and ivfflat and hnsw access methods';


--
-- Name: access_control_model; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.access_control_model AS ENUM (
    'role_based',
    'permission_based'
);


ALTER TYPE public.access_control_model OWNER TO postgres;

--
-- Name: branch_status; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.branch_status AS ENUM (
    'active',
    'merged',
    'archived',
    'deleted'
);


ALTER TYPE public.branch_status OWNER TO postgres;

--
-- Name: conversation_type; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.conversation_type AS ENUM (
    'AI',
    'GROUP',
    'PDF',
    'DROP',
    'AGENTIC'
);


ALTER TYPE public.conversation_type OWNER TO postgres;

--
-- Name: crdt_state_type; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.crdt_state_type AS ENUM (
    'yjs',
    'automerge',
    'json'
);


ALTER TYPE public.crdt_state_type OWNER TO postgres;

--
-- Name: message_type; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.message_type AS ENUM (
    'text',
    'file',
    'image',
    'system'
);


ALTER TYPE public.message_type OWNER TO postgres;

--
-- Name: permission_type; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.permission_type AS ENUM (
    'read',
    'write',
    'admin'
);


ALTER TYPE public.permission_type OWNER TO postgres;

--
-- Name: project_role; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.project_role AS ENUM (
    'owner',
    'admin',
    'writer',
    'reader'
);


ALTER TYPE public.project_role OWNER TO postgres;

--
-- Name: accept_project_invitation(text, uuid); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.accept_project_invitation(p_invitation_token text, p_user_id uuid) RETURNS boolean
    LANGUAGE plpgsql
    AS $$
            DECLARE
                v_invitation RECORD;
                v_user_email TEXT;
            BEGIN
                SELECT email INTO v_user_email FROM users WHERE id = p_user_id;
                
                SELECT * INTO v_invitation 
                FROM project_invitations 
                WHERE invitation_token = p_invitation_token
                  AND expires_at > now()
                  AND accepted_at IS NULL 
                  AND declined_at IS NULL 
                  AND cancelled_at IS NULL;
                
                IF NOT FOUND THEN
                    RETURN FALSE;
                END IF;
                
                UPDATE project_invitations 
                SET accepted_at = now(), accepted_by = p_user_id
                WHERE id = v_invitation.id;
                
                INSERT INTO project_members (user_id, project_id, role)
                VALUES (p_user_id, v_invitation.project_id, v_invitation.role)
                ON CONFLICT (user_id, project_id) DO NOTHING;
                
                IF v_invitation.permission IS NOT NULL THEN
                    INSERT INTO project_collaborators (user_id, project_id, permission)
                    VALUES (p_user_id, v_invitation.project_id, v_invitation.permission)
                    ON CONFLICT (project_id, user_id) DO NOTHING;
                END IF;
                
                RETURN TRUE;
            END;
            $$;


ALTER FUNCTION public.accept_project_invitation(p_invitation_token text, p_user_id uuid) OWNER TO postgres;

--
-- Name: create_project_invitation(uuid, uuid, text, public.project_role, public.permission_type, text, integer); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.create_project_invitation(p_project_id uuid, p_invited_by uuid, p_email text, p_role public.project_role DEFAULT 'reader'::public.project_role, p_permission public.permission_type DEFAULT NULL::public.permission_type, p_message text DEFAULT NULL::text, p_expires_days integer DEFAULT 7) RETURNS uuid
    LANGUAGE plpgsql
    AS $$
            DECLARE
                v_invitation_id UUID;
                v_token TEXT;
            BEGIN
                v_token := encode(gen_random_bytes(32), 'base64url');
                
                IF EXISTS (
                    SELECT 1 FROM project_invitations 
                    WHERE project_id = p_project_id 
                      AND email = p_email 
                      AND accepted_at IS NULL 
                      AND declined_at IS NULL 
                      AND cancelled_at IS NULL 
                      AND expires_at > now()
                ) THEN
                    RAISE EXCEPTION 'Active invitation already exists for this email and project';
                END IF;
                
                INSERT INTO project_invitations (
                    project_id, invited_by, email, role, permission, 
                    invitation_token, message, expires_at
                ) VALUES (
                    p_project_id, p_invited_by, p_email, p_role, p_permission,
                    v_token, p_message, now() + (p_expires_days || ' days')::INTERVAL
                ) RETURNING id INTO v_invitation_id;
                
                RETURN v_invitation_id;
            END;
            $$;


ALTER FUNCTION public.create_project_invitation(p_project_id uuid, p_invited_by uuid, p_email text, p_role public.project_role, p_permission public.permission_type, p_message text, p_expires_days integer) OWNER TO postgres;

--
-- Name: track_feature_usage(uuid, text, text, uuid, jsonb, integer, boolean); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.track_feature_usage(p_user_id uuid, p_feature_name text, p_feature_category text, p_session_id uuid DEFAULT NULL::uuid, p_metadata jsonb DEFAULT NULL::jsonb, p_duration_seconds integer DEFAULT NULL::integer, p_success boolean DEFAULT true) RETURNS void
    LANGUAGE plpgsql
    AS $$
            BEGIN
                INSERT INTO user_feature_usage (
                    user_id, feature_name, feature_category, session_id, 
                    metadata, duration_seconds, success
                ) VALUES (
                    p_user_id, p_feature_name, p_feature_category, p_session_id,
                    p_metadata, p_duration_seconds, p_success
                );
                
                INSERT INTO user_engagement_daily (user_id, date, features_used)
                VALUES (p_user_id, CURRENT_DATE, ARRAY[p_feature_name])
                ON CONFLICT (user_id, date) 
                DO UPDATE SET 
                    features_used = array_append(
                        CASE WHEN p_feature_name = ANY(user_engagement_daily.features_used) 
                             THEN user_engagement_daily.features_used
                             ELSE user_engagement_daily.features_used 
                        END, 
                        CASE WHEN p_feature_name = ANY(user_engagement_daily.features_used)
                             THEN NULL
                             ELSE p_feature_name
                        END
                    );
            END;
            $$;


ALTER FUNCTION public.track_feature_usage(p_user_id uuid, p_feature_name text, p_feature_category text, p_session_id uuid, p_metadata jsonb, p_duration_seconds integer, p_success boolean) OWNER TO postgres;

--
-- Name: update_updated_at_column(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.update_updated_at_column() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
            BEGIN
                NEW.updated_at = now();
                RETURN NEW;
            END;
            $$;


ALTER FUNCTION public.update_updated_at_column() OWNER TO postgres;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: ab_test_participants; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.ab_test_participants (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid,
    test_name text NOT NULL,
    variant text NOT NULL,
    assigned_at timestamp with time zone DEFAULT now(),
    converted boolean DEFAULT false,
    conversion_date timestamp with time zone
);


ALTER TABLE public.ab_test_participants OWNER TO postgres;

--
-- Name: audit_log; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.audit_log (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid,
    action text NOT NULL,
    entity_type text NOT NULL,
    entity_id uuid,
    old_values jsonb,
    new_values jsonb,
    ip_address inet,
    user_agent text,
    created_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.audit_log OWNER TO postgres;

--
-- Name: autosave_queue; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.autosave_queue (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    file_id uuid NOT NULL,
    branch_id uuid NOT NULL,
    change_summary text,
    user_id uuid NOT NULL,
    content_snapshot text,
    priority integer DEFAULT 0,
    status text DEFAULT 'pending'::text,
    scheduled_at timestamp with time zone DEFAULT now(),
    processed_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now(),
    CONSTRAINT autosave_queue_status_check CHECK ((status = ANY (ARRAY['pending'::text, 'processing'::text, 'completed'::text, 'failed'::text])))
);


ALTER TABLE public.autosave_queue OWNER TO postgres;

--
-- Name: branch_permissions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.branch_permissions (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    branch_id uuid NOT NULL,
    user_id uuid NOT NULL,
    can_read boolean DEFAULT true,
    can_write boolean DEFAULT false,
    can_admin boolean DEFAULT false,
    granted_by uuid NOT NULL,
    granted_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.branch_permissions OWNER TO postgres;

--
-- Name: branches; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.branches (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    project_id uuid NOT NULL,
    name text NOT NULL,
    description text,
    source_branch_id uuid,
    head_commit_hash text,
    status public.branch_status DEFAULT 'active'::public.branch_status,
    is_default boolean DEFAULT false,
    is_protected boolean DEFAULT false,
    created_by uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    merged_at timestamp with time zone,
    merged_by uuid,
    deleted_at timestamp with time zone,
    CONSTRAINT no_self_source CHECK ((id <> source_branch_id))
);


ALTER TABLE public.branches OWNER TO postgres;

--
-- Name: conversations; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.conversations (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    type public.conversation_type NOT NULL,
    entity uuid,
    is_group boolean DEFAULT false,
    created_by uuid,
    group_key_encrypted jsonb,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.conversations OWNER TO postgres;

--
-- Name: diagnostics; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.diagnostics (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    paper_id uuid,
    abstract text,
    summary text,
    method text,
    dataset text,
    highlights text,
    weakness text,
    future_scope text,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    strengths text,
    contributions text,
    limitations text
);


ALTER TABLE public.diagnostics OWNER TO postgres;

--
-- Name: document_sessions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.document_sessions (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    file_id uuid NOT NULL,
    session_token text NOT NULL,
    crdt_state jsonb,
    crdt_type public.crdt_state_type DEFAULT 'yjs'::public.crdt_state_type,
    active_users jsonb DEFAULT '[]'::jsonb,
    last_activity timestamp with time zone DEFAULT now(),
    autosave_pending boolean DEFAULT false,
    created_at timestamp with time zone DEFAULT now(),
    expires_at timestamp with time zone DEFAULT (now() + '24:00:00'::interval)
);


ALTER TABLE public.document_sessions OWNER TO postgres;

--
-- Name: email_verification_tokens; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.email_verification_tokens (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid,
    email text NOT NULL,
    token text NOT NULL,
    expires_at timestamp with time zone NOT NULL,
    verified_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.email_verification_tokens OWNER TO postgres;

--
-- Name: feature_analytics; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.feature_analytics (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    feature_name text NOT NULL,
    feature_category text NOT NULL,
    date date NOT NULL,
    total_uses integer DEFAULT 0,
    unique_users integer DEFAULT 0,
    avg_duration_seconds numeric,
    success_rate numeric,
    created_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.feature_analytics OWNER TO postgres;

--
-- Name: file_uploads; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.file_uploads (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid,
    original_filename text NOT NULL,
    stored_filename text NOT NULL,
    file_path text NOT NULL,
    file_size bigint,
    mime_type text,
    checksum text,
    uploaded_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.file_uploads OWNER TO postgres;

--
-- Name: git_repositories; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.git_repositories (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    project_id uuid NOT NULL,
    repo_path text NOT NULL,
    repo_url text,
    default_branch_id uuid,
    last_commit_hash text,
    initialized boolean DEFAULT false,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.git_repositories OWNER TO postgres;

--
-- Name: graphs; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.graphs (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    project_id uuid,
    graph_path text NOT NULL,
    graph_type text DEFAULT 'knowledge_graph'::text,
    metadata jsonb,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.graphs OWNER TO postgres;

--
-- Name: highlights; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.highlights (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid,
    paper_id uuid,
    project_id uuid,
    name text,
    is_public boolean DEFAULT false,
    start_pos integer[],
    end_pos integer[],
    content text,
    color text DEFAULT '#ffff00'::text,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.highlights OWNER TO postgres;

--
-- Name: invitation_reminders; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.invitation_reminders (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    invitation_id uuid,
    sent_at timestamp with time zone DEFAULT now(),
    reminder_count integer DEFAULT 1
);


ALTER TABLE public.invitation_reminders OWNER TO postgres;

--
-- Name: latex_comments; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.latex_comments (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    project_id uuid,
    commit_hash text NOT NULL,
    user_id uuid,
    content text NOT NULL,
    line_number integer,
    file_path text,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.latex_comments OWNER TO postgres;

--
-- Name: latex_commits; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.latex_commits (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    project_id uuid,
    user_id uuid,
    commit_hash text NOT NULL,
    message text,
    parent_commit text,
    branch text DEFAULT 'main'::text,
    created_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.latex_commits OWNER TO postgres;

--
-- Name: latex_conflicts; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.latex_conflicts (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    project_id uuid,
    base_commit text NOT NULL,
    target_commit text NOT NULL,
    conflict_file text NOT NULL,
    conflict_section text,
    resolution text,
    resolved_by uuid,
    created_at timestamp with time zone DEFAULT now(),
    resolved_at timestamp with time zone,
    resolved boolean DEFAULT false
);


ALTER TABLE public.latex_conflicts OWNER TO postgres;

--
-- Name: latex_files; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.latex_files (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    project_id uuid NOT NULL,
    branch_id uuid NOT NULL,
    file_path text NOT NULL,
    file_name text NOT NULL,
    file_type text DEFAULT 'tex'::text,
    file_size bigint DEFAULT 0,
    encoding text DEFAULT 'utf-8'::text,
    created_by uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    last_modified_by uuid,
    deleted_at timestamp with time zone
);


ALTER TABLE public.latex_files OWNER TO postgres;

--
-- Name: latex_snapshots; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.latex_snapshots (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    project_id uuid,
    commit_hash text NOT NULL,
    label text NOT NULL,
    description text,
    user_id uuid,
    created_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.latex_snapshots OWNER TO postgres;

--
-- Name: notes; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.notes (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid,
    paper_id uuid,
    project_id uuid,
    name text,
    is_public boolean DEFAULT false,
    text text NOT NULL,
    "position" integer[],
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.notes OWNER TO postgres;

--
-- Name: paper_embeddings; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.paper_embeddings (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    paper_id uuid NOT NULL,
    embedding_model text DEFAULT 'all-MiniLM-L6-v2'::text NOT NULL,
    title_embedding public.vector(384),
    abstract_embedding public.vector(384),
    combined_embedding public.vector(384),
    embedding_created_at timestamp with time zone DEFAULT now(),
    embedding_updated_at timestamp with time zone DEFAULT now(),
    embedding public.vector(384),
    source_text text,
    model_name text DEFAULT 'all-MiniLM-L6-v2'::text,
    processing_status text DEFAULT 'completed'::text,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    error_message text,
    model_version text,
    embedding_metadata jsonb
);


ALTER TABLE public.paper_embeddings OWNER TO postgres;

--
-- Name: papers; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.papers (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    title text NOT NULL,
    date_added timestamp with time zone DEFAULT now(),
    last_modified timestamp with time zone DEFAULT now(),
    pdf_path text,
    bib_path text,
    file_size bigint,
    mime_type text,
    checksum text,
    private_uploaded boolean DEFAULT false,
    authors text[],
    keywords text[],
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    deleted_at timestamp with time zone,
    xml_path text,
    arxiv_id text,
    doi text,
    abstract text,
    safe_title text
);


ALTER TABLE public.papers OWNER TO postgres;

--
-- Name: password_reset_tokens; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.password_reset_tokens (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid,
    token text NOT NULL,
    expires_at timestamp with time zone NOT NULL,
    used boolean DEFAULT false,
    created_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.password_reset_tokens OWNER TO postgres;

--
-- Name: performance_metrics; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.performance_metrics (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    metric_name text NOT NULL,
    metric_category text NOT NULL,
    value numeric NOT NULL,
    unit text NOT NULL,
    metadata jsonb,
    recorded_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.performance_metrics OWNER TO postgres;

--
-- Name: project_collaborators; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.project_collaborators (
    project_id uuid NOT NULL,
    user_id uuid NOT NULL,
    permission public.permission_type NOT NULL,
    added_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.project_collaborators OWNER TO postgres;

--
-- Name: project_invitations; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.project_invitations (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    project_id uuid,
    invited_by uuid,
    email text NOT NULL,
    role public.project_role DEFAULT 'reader'::public.project_role NOT NULL,
    permission public.permission_type,
    invitation_token text NOT NULL,
    message text,
    expires_at timestamp with time zone DEFAULT (now() + '7 days'::interval) NOT NULL,
    accepted_at timestamp with time zone,
    accepted_by uuid,
    declined_at timestamp with time zone,
    cancelled_at timestamp with time zone,
    cancelled_by uuid,
    created_at timestamp with time zone DEFAULT now(),
    CONSTRAINT check_invitation_state CHECK ((((accepted_at IS NULL) AND (declined_at IS NULL) AND (cancelled_at IS NULL)) OR ((accepted_at IS NOT NULL) AND (declined_at IS NULL) AND (cancelled_at IS NULL)) OR ((accepted_at IS NULL) AND (declined_at IS NOT NULL) AND (cancelled_at IS NULL)) OR ((accepted_at IS NULL) AND (declined_at IS NULL) AND (cancelled_at IS NOT NULL))))
);


ALTER TABLE public.project_invitations OWNER TO postgres;

--
-- Name: project_members; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.project_members (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid,
    project_id uuid,
    role public.project_role DEFAULT 'reader'::public.project_role NOT NULL,
    added_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.project_members OWNER TO postgres;

--
-- Name: project_papers; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.project_papers (
    project_id uuid NOT NULL,
    paper_id uuid NOT NULL,
    uploaded boolean DEFAULT true,
    added_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.project_papers OWNER TO postgres;

--
-- Name: projects; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.projects (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    name text NOT NULL,
    slug text,
    description text,
    conversation_id uuid,
    repo_url text,
    created_by uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    deleted_at timestamp with time zone,
    access_model public.access_control_model DEFAULT 'role_based'::public.access_control_model NOT NULL
);


ALTER TABLE public.projects OWNER TO postgres;

--
-- Name: system_settings; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.system_settings (
    key text NOT NULL,
    value jsonb NOT NULL,
    description text,
    updated_at timestamp with time zone DEFAULT now(),
    updated_by uuid
);


ALTER TABLE public.system_settings OWNER TO postgres;

--
-- Name: task_activity; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.task_activity (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    task_id uuid,
    user_id uuid,
    action text NOT NULL,
    field_changed text,
    old_value text,
    new_value text,
    created_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.task_activity OWNER TO postgres;

--
-- Name: task_assignees; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.task_assignees (
    task_id uuid NOT NULL,
    user_id uuid NOT NULL,
    assigned_by uuid,
    assigned_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.task_assignees OWNER TO postgres;

--
-- Name: task_attachments; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.task_attachments (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    task_id uuid,
    file_id uuid,
    paper_id uuid,
    attached_by uuid,
    attached_at timestamp with time zone DEFAULT now(),
    CONSTRAINT attachment_type_check CHECK ((((file_id IS NOT NULL) AND (paper_id IS NULL)) OR ((file_id IS NULL) AND (paper_id IS NOT NULL))))
);


ALTER TABLE public.task_attachments OWNER TO postgres;

--
-- Name: task_comments; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.task_comments (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    task_id uuid,
    user_id uuid,
    content text NOT NULL,
    reply_to uuid,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    deleted_at timestamp with time zone
);


ALTER TABLE public.task_comments OWNER TO postgres;

--
-- Name: task_dependencies; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.task_dependencies (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    predecessor_task_id uuid,
    successor_task_id uuid,
    dependency_type text DEFAULT 'finish_to_start'::text,
    created_at timestamp with time zone DEFAULT now(),
    CONSTRAINT no_self_dependency CHECK ((predecessor_task_id <> successor_task_id)),
    CONSTRAINT task_dependencies_dependency_type_check CHECK ((dependency_type = ANY (ARRAY['finish_to_start'::text, 'start_to_start'::text, 'finish_to_finish'::text, 'start_to_finish'::text])))
);


ALTER TABLE public.task_dependencies OWNER TO postgres;

--
-- Name: task_lists; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.task_lists (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    project_id uuid,
    name text NOT NULL,
    description text,
    color text DEFAULT '#3498db'::text,
    "position" integer DEFAULT 0,
    created_by uuid,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.task_lists OWNER TO postgres;

--
-- Name: task_recurrence; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.task_recurrence (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    task_id uuid,
    recurrence_type text NOT NULL,
    recurrence_interval integer DEFAULT 1,
    days_of_week integer[],
    day_of_month integer,
    end_date timestamp with time zone,
    max_occurrences integer,
    created_at timestamp with time zone DEFAULT now(),
    CONSTRAINT task_recurrence_recurrence_type_check CHECK ((recurrence_type = ANY (ARRAY['daily'::text, 'weekly'::text, 'monthly'::text, 'quarterly'::text, 'yearly'::text])))
);


ALTER TABLE public.task_recurrence OWNER TO postgres;

--
-- Name: task_tags; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.task_tags (
    task_id uuid NOT NULL,
    tag_id uuid NOT NULL,
    user_id uuid NOT NULL,
    tagged_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.task_tags OWNER TO postgres;

--
-- Name: task_time_logs; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.task_time_logs (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    task_id uuid,
    user_id uuid,
    description text,
    hours numeric(5,2) NOT NULL,
    log_date date DEFAULT CURRENT_DATE,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    CONSTRAINT task_time_logs_hours_check CHECK ((hours > (0)::numeric))
);


ALTER TABLE public.task_time_logs OWNER TO postgres;

--
-- Name: task_watchers; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.task_watchers (
    task_id uuid NOT NULL,
    user_id uuid NOT NULL,
    watched_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.task_watchers OWNER TO postgres;

--
-- Name: tasks; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tasks (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    project_id uuid,
    task_list_id uuid,
    parent_task_id uuid,
    title text NOT NULL,
    description text,
    status text DEFAULT 'todo'::text,
    priority text DEFAULT 'medium'::text,
    due_date timestamp with time zone,
    start_date timestamp with time zone,
    estimated_hours numeric(5,2),
    actual_hours numeric(5,2),
    progress integer DEFAULT 0,
    created_by uuid,
    assigned_to uuid,
    "position" integer DEFAULT 0,
    is_milestone boolean DEFAULT false,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    completed_at timestamp with time zone,
    deleted_at timestamp with time zone,
    CONSTRAINT tasks_priority_check CHECK ((priority = ANY (ARRAY['low'::text, 'medium'::text, 'high'::text, 'urgent'::text]))),
    CONSTRAINT tasks_progress_check CHECK (((progress >= 0) AND (progress <= 100))),
    CONSTRAINT tasks_status_check CHECK ((status = ANY (ARRAY['todo'::text, 'in_progress'::text, 'review'::text, 'done'::text, 'cancelled'::text])))
);


ALTER TABLE public.tasks OWNER TO postgres;

--
-- Name: user_behavior_patterns; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.user_behavior_patterns (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid,
    pattern_type text NOT NULL,
    pattern_data jsonb NOT NULL,
    confidence_score numeric(3,2),
    last_updated timestamp with time zone DEFAULT now(),
    created_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.user_behavior_patterns OWNER TO postgres;

--
-- Name: user_engagement_daily; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.user_engagement_daily (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid,
    date date NOT NULL,
    total_sessions integer DEFAULT 0,
    total_time_minutes integer DEFAULT 0,
    features_used text[],
    papers_interacted integer DEFAULT 0,
    highlights_created integer DEFAULT 0,
    notes_created integer DEFAULT 0,
    chat_messages_sent integer DEFAULT 0,
    ai_interactions integer DEFAULT 0,
    latex_commits integer DEFAULT 0,
    login_count integer DEFAULT 0,
    created_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.user_engagement_daily OWNER TO postgres;

--
-- Name: user_feature_usage; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.user_feature_usage (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid,
    feature_name text NOT NULL,
    feature_category text NOT NULL,
    session_id uuid,
    metadata jsonb,
    duration_seconds integer,
    success boolean DEFAULT true,
    created_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.user_feature_usage OWNER TO postgres;

--
-- Name: user_paper_tags; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.user_paper_tags (
    user_id uuid NOT NULL,
    paper_id uuid NOT NULL,
    tag_id uuid NOT NULL,
    tagged_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.user_paper_tags OWNER TO postgres;

--
-- Name: user_project_tags; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.user_project_tags (
    user_id uuid NOT NULL,
    project_id uuid NOT NULL,
    tag_id uuid NOT NULL,
    tagged_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.user_project_tags OWNER TO postgres;

--
-- Name: user_saved_searches; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.user_saved_searches (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid NOT NULL,
    name text NOT NULL,
    search_query text NOT NULL,
    filters jsonb DEFAULT '{}'::jsonb,
    is_private boolean DEFAULT true,
    search_count integer DEFAULT 0,
    last_used_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.user_saved_searches OWNER TO postgres;

--
-- Name: user_sessions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.user_sessions (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid,
    token_hash text NOT NULL,
    expires_at timestamp with time zone NOT NULL,
    created_at timestamp with time zone DEFAULT now(),
    last_used_at timestamp with time zone DEFAULT now(),
    user_agent text,
    ip_address inet
);


ALTER TABLE public.user_sessions OWNER TO postgres;

--
-- Name: user_sessions_detailed; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.user_sessions_detailed (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid,
    session_token uuid NOT NULL,
    start_time timestamp with time zone DEFAULT now(),
    end_time timestamp with time zone,
    duration_minutes integer,
    pages_visited text[],
    features_used text[],
    projects_accessed uuid[],
    papers_accessed uuid[],
    device_type text,
    browser text,
    ip_address inet,
    referrer text,
    exit_page text
);


ALTER TABLE public.user_sessions_detailed OWNER TO postgres;

--
-- Name: user_tags; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.user_tags (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid,
    name text NOT NULL,
    color text DEFAULT '#808080'::text,
    created_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.user_tags OWNER TO postgres;

--
-- Name: users; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.users (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    name text NOT NULL,
    email text NOT NULL,
    password text NOT NULL,
    public_key text,
    email_verified boolean DEFAULT false,
    accepted_terms boolean DEFAULT false,
    interests text[],
    intro text DEFAULT 'Fill in your information'::text,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    last_login timestamp with time zone,
    deleted_at timestamp with time zone,
    CONSTRAINT users_email_check CHECK ((email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'::text))
);


ALTER TABLE public.users OWNER TO postgres;

--
-- Data for Name: ab_test_participants; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.ab_test_participants (id, user_id, test_name, variant, assigned_at, converted, conversion_date) FROM stdin;
\.


--
-- Data for Name: audit_log; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.audit_log (id, user_id, action, entity_type, entity_id, old_values, new_values, ip_address, user_agent, created_at) FROM stdin;
\.


--
-- Data for Name: autosave_queue; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.autosave_queue (id, file_id, branch_id, change_summary, user_id, content_snapshot, priority, status, scheduled_at, processed_at, created_at) FROM stdin;
\.


--
-- Data for Name: branch_permissions; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.branch_permissions (id, branch_id, user_id, can_read, can_write, can_admin, granted_by, granted_at) FROM stdin;
069d2a61-b08d-417f-b0dd-fc00b2230e0f	d1b97253-d447-4949-a01e-850be870a414	ff40fb7e-b5b8-436a-b16f-cc4a31146ff5	t	t	t	ff40fb7e-b5b8-436a-b16f-cc4a31146ff5	2025-08-03 19:49:53.96827+00
c937689e-c536-4ce3-9e3d-8fc6456113d1	5eed7bd3-d185-477c-8303-a13f6e5352f6	ff40fb7e-b5b8-436a-b16f-cc4a31146ff5	t	t	t	ff40fb7e-b5b8-436a-b16f-cc4a31146ff5	2025-08-03 20:24:04.635136+00
dd00fdeb-d427-4453-8915-4c1b70a04a0c	d92cd427-0790-40e5-932e-807ca28fc8f7	ff40fb7e-b5b8-436a-b16f-cc4a31146ff5	t	t	t	ff40fb7e-b5b8-436a-b16f-cc4a31146ff5	2025-08-03 20:39:01.347069+00
\.


--
-- Data for Name: branches; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.branches (id, project_id, name, description, source_branch_id, head_commit_hash, status, is_default, is_protected, created_by, created_at, updated_at, merged_at, merged_by, deleted_at) FROM stdin;
d1b97253-d447-4949-a01e-850be870a414	36eae63b-2fc6-4543-acab-2197c8a3cff6	main	Main development branch	\N	eddae62b42a3a9b2a5d7d2ff6d8f8dc48d89693e	active	t	f	ff40fb7e-b5b8-436a-b16f-cc4a31146ff5	2025-08-03 19:49:53.96827+00	2025-08-03 19:49:53.96827+00	\N	\N	\N
5eed7bd3-d185-477c-8303-a13f6e5352f6	28f846fd-e8f5-48dd-814e-526854578e3a	main	Main development branch	\N	c0ff347a38860cef7faf08bf81dfffad1baa794d	active	t	f	ff40fb7e-b5b8-436a-b16f-cc4a31146ff5	2025-08-03 20:24:04.635136+00	2025-08-03 20:24:04.635136+00	\N	\N	\N
d92cd427-0790-40e5-932e-807ca28fc8f7	7b2f8acd-a112-45f7-b166-3ba25f95e669	main	Main development branch	\N	8b483ec1f7bcd93805c1b65fbeda74c3db8e9120	active	t	f	ff40fb7e-b5b8-436a-b16f-cc4a31146ff5	2025-08-03 20:39:01.347069+00	2025-08-03 20:39:01.347069+00	\N	\N	\N
\.


--
-- Data for Name: conversations; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.conversations (id, type, entity, is_group, created_by, group_key_encrypted, created_at, updated_at) FROM stdin;
043dbee7-c490-405b-86d4-6bcb84d54058	GROUP	36eae63b-2fc6-4543-acab-2197c8a3cff6	t	ff40fb7e-b5b8-436a-b16f-cc4a31146ff5	null	2025-08-03 19:50:19.372767+00	2025-08-03 19:50:19.372767+00
3183228d-b4e9-4ea0-8b32-bd6d12bac221	AI	36eae63b-2fc6-4543-acab-2197c8a3cff6	f	ff40fb7e-b5b8-436a-b16f-cc4a31146ff5	null	2025-08-03 19:51:10.727934+00	2025-08-03 19:51:10.727934+00
c38e8bf3-de05-41c8-b852-0fec0445beb2	AGENTIC	36eae63b-2fc6-4543-acab-2197c8a3cff6	f	ff40fb7e-b5b8-436a-b16f-cc4a31146ff5	null	2025-08-03 19:52:19.174779+00	2025-08-03 19:52:19.174779+00
06bcdb1a-7fb2-4749-bc80-55f501197d16	AGENTIC	36eae63b-2fc6-4543-acab-2197c8a3cff6	f	ff40fb7e-b5b8-436a-b16f-cc4a31146ff5	null	2025-08-03 19:54:14.327552+00	2025-08-03 19:54:14.327552+00
263d5f17-4fdb-4cee-83dd-a71a653aac46	GROUP	28f846fd-e8f5-48dd-814e-526854578e3a	t	ff40fb7e-b5b8-436a-b16f-cc4a31146ff5	null	2025-08-03 20:24:28.63956+00	2025-08-03 20:24:28.63956+00
cb4671e5-9adf-4904-ab57-18f961c42027	AGENTIC	28f846fd-e8f5-48dd-814e-526854578e3a	f	ff40fb7e-b5b8-436a-b16f-cc4a31146ff5	null	2025-08-03 20:27:30.051773+00	2025-08-03 20:27:30.051773+00
50dde758-1a6c-44ba-8ffa-6e10fe7dde0f	AGENTIC	28f846fd-e8f5-48dd-814e-526854578e3a	f	ff40fb7e-b5b8-436a-b16f-cc4a31146ff5	null	2025-08-03 20:37:32.966536+00	2025-08-03 20:37:32.966536+00
e5e445fd-486a-4ddd-8e58-75e74e9dfe50	AGENTIC	28f846fd-e8f5-48dd-814e-526854578e3a	f	ff40fb7e-b5b8-436a-b16f-cc4a31146ff5	null	2025-08-03 20:37:46.121479+00	2025-08-03 20:37:46.121479+00
a3b1c3f7-dd64-4080-b935-6ad4536f1581	GROUP	7b2f8acd-a112-45f7-b166-3ba25f95e669	t	ff40fb7e-b5b8-436a-b16f-cc4a31146ff5	null	2025-08-03 20:39:03.493896+00	2025-08-03 20:39:03.493896+00
fe45bb78-4613-40a6-ba9e-75f560ed1514	AGENTIC	7b2f8acd-a112-45f7-b166-3ba25f95e669	f	ff40fb7e-b5b8-436a-b16f-cc4a31146ff5	null	2025-08-03 20:39:20.617206+00	2025-08-03 20:39:20.617206+00
89da3c57-2d65-4dc2-96fa-2e8220641644	DROP	7b2f8acd-a112-45f7-b166-3ba25f95e669	f	ff40fb7e-b5b8-436a-b16f-cc4a31146ff5	null	2025-08-03 20:41:09.10016+00	2025-08-03 20:41:09.10016+00
\.


--
-- Data for Name: diagnostics; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.diagnostics (id, paper_id, abstract, summary, method, dataset, highlights, weakness, future_scope, created_at, updated_at, strengths, contributions, limitations) FROM stdin;
655b81fb-545e-4a0e-baab-dead69565842	77ec8d85-6e43-4254-aa0e-038b3a585cca	This paper addresses the limitations of existing sequence transduction models, which rely on complex recurrent or convolutional neural networks, by proposing a novel architecture called the Transformer. The Transformer is solely based on attention mechanisms, eliminating the need for recurrence and convolutions, thereby enhancing parallelization and reducing training time. Experimental results demonstrate that the Transformer achieves state-of-the-art performance on machine translation tasks, with significant improvements in BLEU scores over previous models. The broader implications suggest that this architecture could revolutionize sequence modeling across various natural language processing tasks due to its efficiency and effectiveness.	This paper addresses the limitations of existing sequence transduction models, which rely on complex recurrent or convolutional neural networks, by proposing a novel architecture called the Transformer. The Transformer is solely based on attention mechanisms, eliminating the need for recurrence and convolutions, thereby enhancing parallelization and reducing training time. Experimental results demonstrate that the Transformer achieves state-of-the-art performance on machine translation tasks, with significant improvements in BLEU scores over previous models. The broader implications suggest that this architecture could revolutionize sequence modeling across various natural language processing tasks due to its efficiency and effectiveness.	{'experimental_design': 'The study employs a comparative experimental design, evaluating the Transformer against established recurrent and convolutional models on machine translation tasks.', 'theoretical_framework': 'The theoretical framework is grounded in attention mechanisms, particularly self-attention, which allows the model to weigh the importance of different words in a sequence without relying on sequential processing.', 'technical_approach': 'The Transformer architecture consists of an encoder-decoder structure where both components utilize multi-head self-attention and feed-forward neural networks. The model processes input sequences in parallel, significantly improving computational efficiency.', 'validation_strategy': 'Validation is conducted through extensive experiments on two benchmark machine translation datasets (WMT 2014 English-to-German and English-to-French), measuring performance using BLEU scores.', 'novel_methodological_contributions': 'The introduction of scaled dot-product attention and multi-head attention mechanisms represents a significant methodological innovation, allowing for richer representations of input sequences.'}	{'dataset_names': ['WMT 2014 English-to-German', 'WMT 2014 English-to-French'], 'sizes': 'Not clearly specified in the provided text', 'characteristics': 'The datasets are standard benchmarks for machine translation, comprising pairs of sentences in English and their corresponding translations in German and French.', 'preprocessing_steps': 'Not clearly specified in the provided text', 'evaluation_metrics': 'BLEU scores are used as the primary metric for evaluating translation quality.', 'data_limitations': 'Potential biases in the datasets may affect generalizability, particularly if the training data does not adequately represent the diversity of language use.'}	Introduced the Transformer architecture, which relies entirely on attention mechanisms, improving training speed and efficiency.; Achieved state-of-the-art BLEU scores on both English-to-German and English-to-French translation tasks, surpassing previous models.; Demonstrated the model's versatility by successfully applying it to English constituency parsing with varying amounts of training data.; Established a new benchmark for training time efficiency, completing training in a fraction of the time required by earlier models.	The paper does not provide detailed information on the preprocessing steps for the datasets, which may affect reproducibility.; Limited discussion on potential biases in the datasets used could raise questions about the generalizability of the findings.; The focus on machine translation may limit the exploration of the Transformer's applicability to other domains beyond natural language processing.	Exploration of the Transformer's application to other NLP tasks, such as summarization or question answering.; Investigation into the impact of different attention mechanisms and model architectures on performance and efficiency.; Development of methods to mitigate biases in training datasets to enhance model generalizability.; Potential collaborations with researchers in other domains to adapt the Transformer architecture for non-NLP applications.	2025-08-03 19:53:00.579472+00	2025-08-03 19:53:00.579472+00	The paper presents a novel and efficient architecture that significantly advances the state of the art in machine translation.; Methodological rigor is evident in the experimental design and comprehensive evaluation of the model's performance.; The clarity of presentation and thoroughness in explaining the architecture and its components enhance understanding and reproducibility.; The results are compelling, demonstrating substantial improvements over existing models, which underscores the significance of the research.	The introduction of the Transformer architecture represents a major advancement in the field of sequence modeling.; Empirical evidence provided through extensive experiments establishes the superiority of the Transformer in machine translation tasks.; The study offers theoretical insights into the effectiveness of attention mechanisms, paving the way for future research in this area.; Methodological innovations, such as multi-head attention, contribute to the development of more efficient and effective NLP models.	The study primarily focuses on machine translation, which may restrict the applicability of the findings to other NLP tasks.; The evaluation metrics are limited to BLEU scores, which, while standard, may not capture all aspects of translation quality.; The model's performance on languages with less training data or different linguistic structures is not addressed.
b9863f93-5fbf-4c8f-b056-69f1a2b7c0b2	8795f4f7-7a94-4e3e-9128-2a23e1c7ee0c	This paper addresses the challenge of crowd counting in images, particularly in the presence of perspective distortion, by proposing a novel end-to-end trainable deep architecture. The authors introduce a method that extracts features using multiple receptive field sizes and learns the significance of each feature at every image location, allowing for adaptive scale encoding. Key experimental findings demonstrate that this approach outperforms existing state-of-the-art methods, especially in scenarios with strong perspective effects. The broader implications suggest that this methodology could enhance applications in video surveillance and traffic control by providing more accurate crowd density estimations.	This paper addresses the challenge of crowd counting in images, particularly in the presence of perspective distortion, by proposing a novel end-to-end trainable deep architecture. The authors introduce a method that extracts features using multiple receptive field sizes and learns the significance of each feature at every image location, allowing for adaptive scale encoding. Key experimental findings demonstrate that this approach outperforms existing state-of-the-art methods, especially in scenarios with strong perspective effects. The broader implications suggest that this methodology could enhance applications in video surveillance and traffic control by providing more accurate crowd density estimations.	The proposed methodology employs a deep learning architecture that integrates features from multiple receptive field sizes, allowing the model to adaptively learn the importance of each feature based on the local context of the image. This is achieved through a convolutional network that processes input images in a way that accounts for varying scales, addressing the limitations of previous methods that used fixed receptive fields. The architecture is designed to be end-to-end trainable, facilitating the learning process without the need for auxiliary classifiers. Validation is performed through extensive experiments comparing the proposed method against existing crowd counting techniques, demonstrating superior performance in various scenarios.	Not clearly specified in the provided text. The paper does not mention specific datasets used for training or testing the model, their sizes, or characteristics. It also lacks details on preprocessing steps, evaluation metrics employed, and any potential biases or limitations in the datasets that could impact the findings.	Introduces an end-to-end trainable deep architecture for crowd counting that effectively utilizes multi-scale contextual information.; Demonstrates significant performance improvements over state-of-the-art methods, particularly in the presence of perspective distortion.; Provides a novel approach to adaptively learn the importance of features at each image location, enhancing the model's flexibility.; Shows that the method can leverage calibration data to further improve crowd density predictions.	The paper lacks detailed information about the datasets used, which raises concerns about the reproducibility and generalizability of the results.; Insufficient baseline comparisons with a wider range of existing methods could limit the assessment of the proposed method's relative performance.; The theoretical framework behind the adaptive learning of feature importance is not thoroughly explained, which may hinder understanding of the underlying mechanisms.	Exploration of additional datasets to validate the model's effectiveness across diverse environments and conditions.; Investigation into the integration of other contextual features or modalities (e.g., temporal information) to further enhance crowd counting accuracy.; Development of methods to improve the model's performance in uncalibrated settings without relying on calibration data.; Potential collaborations with practitioners in surveillance and traffic management to apply the model in real-world scenarios.	2025-08-03 19:54:54.875142+00	2025-08-03 19:54:54.875142+00	The proposed method demonstrates methodological rigor through its end-to-end trainable architecture, which is a significant advancement over previous approaches.; The clarity of presentation allows for a good understanding of the problem addressed and the proposed solution.; Empirical results consistently show improved performance, indicating the practical significance of the research findings.	Advances the field of crowd counting by providing a novel, adaptive approach that incorporates multi-scale contextual information.; Offers empirical evidence supporting the effectiveness of the proposed method in overcoming challenges posed by perspective distortion.; Contributes to the theoretical understanding of feature importance in deep learning models for image analysis.	The study does not provide specific details on the datasets, which may limit the ability to replicate the results.; The focus on perspective distortion may restrict the applicability of the method to other types of crowd counting scenarios.; The model's performance may be contingent on the availability of calibration data, which could limit its use in uncalibrated environments.
6c9dd03a-2d25-479c-950e-154fb0f62cf6	916d8a22-654d-4386-8531-c09844810aca	This paper addresses the challenge of crowd counting in images, particularly under conditions of perspective distortion, by proposing a novel end-to-end trainable deep architecture. The authors introduce a method that adaptively combines features from multiple receptive field sizes, allowing the model to learn the importance of each feature at every image location. Experimental results demonstrate that this approach significantly outperforms existing state-of-the-art methods, especially in scenarios with strong perspective effects. The findings suggest broader implications for improving accuracy in crowd counting applications, such as video surveillance and traffic control.	This paper addresses the challenge of crowd counting in images, particularly under conditions of perspective distortion, by proposing a novel end-to-end trainable deep architecture. The authors introduce a method that adaptively combines features from multiple receptive field sizes, allowing the model to learn the importance of each feature at every image location. Experimental results demonstrate that this approach significantly outperforms existing state-of-the-art methods, especially in scenarios with strong perspective effects. The findings suggest broader implications for improving accuracy in crowd counting applications, such as video surveillance and traffic control.	{'experimental_design': 'The authors developed a deep learning architecture that integrates features from multiple receptive field sizes, allowing for adaptive learning of contextual information across the image. This design enables the model to account for varying scales of crowd density effectively.', 'theoretical_framework': 'The theoretical underpinning is based on the need for varying receptive fields in response to perspective distortion, contrasting with traditional methods that apply uniform filters across images.', 'technical_approach': 'The proposed method employs a convolutional neural network (CNN) architecture that processes input images through multiple convolutional layers with different kernel sizes, enabling the model to learn scale-dependent features.', 'validation_strategy': "The authors validate their approach through extensive experiments on benchmark datasets, comparing their model's performance against existing crowd counting methods using standard evaluation metrics.", 'novel_methodological_contributions': 'The key innovation lies in the end-to-end trainability of the model, which allows for a more flexible and efficient learning process compared to previous methods that relied on fixed receptive fields or separate classifiers.'}	{'dataset_names': 'Not clearly specified in the provided text', 'sizes': 'Not clearly specified in the provided text', 'characteristics': 'Not clearly specified in the provided text', 'preprocessing_steps': 'Not clearly specified in the provided text', 'evaluation_metrics': 'Not clearly specified in the provided text', 'data_limitations': 'Not clearly specified in the provided text'}	Introduced an end-to-end trainable architecture that effectively incorporates multi-scale contextual information for crowd counting.; Demonstrated significant performance improvements over existing methods, particularly in handling perspective distortion.; Provided a novel approach to adaptively learn the importance of features at each image location, enhancing the model's flexibility.; Showed that calibration data can further enhance performance, suggesting a dual approach to crowd counting.	The paper lacks detailed information on the datasets used for validation, which limits the reproducibility of the results.; There is insufficient discussion on the specific evaluation metrics employed, making it difficult to assess the robustness of the findings.; The methodology may not be generalizable to all types of crowd counting scenarios, particularly those with extreme variations in crowd density.	Exploration of additional datasets to validate the proposed method across diverse environments and crowd conditions.; Investigation into the integration of other contextual features beyond scale, such as social interactions among individuals in the crowd.; Development of hybrid models that combine the proposed approach with traditional crowd counting methods for enhanced performance.; Assessment of the model's applicability in real-time crowd counting applications, such as surveillance systems.	2025-08-03 20:27:49.350001+00	2025-08-03 20:27:49.350001+00	The proposed method demonstrates a high level of methodological rigor and innovation in addressing a significant problem in computer vision.; The clarity of presentation and logical flow of the paper facilitate understanding of complex concepts.; Experimental results provide strong empirical evidence supporting the effectiveness of the proposed approach.	Advancement of knowledge in crowd counting methodologies by introducing a flexible, end-to-end trainable model.; Practical applications in areas such as public safety, urban planning, and event management.; Theoretical insights into the importance of multi-scale feature extraction in computer vision tasks.	The study does not specify the datasets or their characteristics, which may affect the generalizability of the results.; The methodology may be limited by the types of images used for training and testing, potentially introducing biases.; The focus on perspective distortion may overlook other factors influencing crowd counting accuracy.
0e8de978-213d-4cd7-a28b-7434a0693097	00b2848f-d0b0-4623-a321-bc74539f9703	This paper addresses the limitations of existing sequence transduction models that rely on recurrent or convolutional neural networks by proposing a novel architecture called the Transformer, which is solely based on attention mechanisms. The authors demonstrate that the Transformer outperforms traditional models in machine translation tasks, achieving state-of-the-art BLEU scores of 28.4 for English-to-German and 41.8 for English-to-French translations, while also being more parallelizable and requiring significantly less training time. The findings suggest that the Transformer architecture not only enhances translation quality but also generalizes well to other tasks, such as English constituency parsing, indicating its broader applicability in natural language processing. This work has significant implications for the design of future neural network architectures, emphasizing the potential of attention mechanisms in overcoming the limitations of recurrent models.	This paper addresses the limitations of existing sequence transduction models that rely on recurrent or convolutional neural networks by proposing a novel architecture called the Transformer, which is solely based on attention mechanisms. The authors demonstrate that the Transformer outperforms traditional models in machine translation tasks, achieving state-of-the-art BLEU scores of 28.4 for English-to-German and 41.8 for English-to-French translations, while also being more parallelizable and requiring significantly less training time. The findings suggest that the Transformer architecture not only enhances translation quality but also generalizes well to other tasks, such as English constituency parsing, indicating its broader applicability in natural language processing. This work has significant implications for the design of future neural network architectures, emphasizing the potential of attention mechanisms in overcoming the limitations of recurrent models.	{'experimental_design': 'The study employs a comparative approach, evaluating the Transformer against existing recurrent and convolutional models on standard machine translation benchmarks.', 'theoretical_framework': 'The Transformer is built on the self-attention mechanism, allowing the model to weigh the importance of different words in a sequence without relying on recurrence or convolutions.', 'technical_approach': 'The architecture consists of an encoder-decoder structure where both components utilize multi-head self-attention and position-wise feedforward networks. The model also incorporates positional encodings to maintain the order of sequences.', 'validation_strategy': "The authors validate their approach through extensive experiments on WMT 2014 translation tasks, comparing BLEU scores against state-of-the-art models, and also evaluate the model's performance on English constituency parsing.", 'novel_methodological_contributions': 'The introduction of the Transformer architecture itself is a significant methodological contribution, particularly the use of self-attention and multi-head attention mechanisms.'}	{'dataset_names': ['WMT 2014 English-to-German', 'WMT 2014 English-to-French'], 'sizes': 'Not clearly specified in the provided text', 'characteristics': 'The datasets consist of parallel corpora for machine translation, commonly used in the NLP community for benchmarking translation models.', 'preprocessing_steps': 'Not clearly specified in the provided text', 'evaluation_metrics': 'BLEU score is used as the primary evaluation metric for translation quality.', 'data_limitations': 'Potential limitations include biases inherent in the training data and the focus on specific language pairs, which may not generalize to other languages or domains.'}	Introduction of the Transformer architecture, which eliminates the need for recurrence and convolutions in sequence transduction tasks.; Achieved state-of-the-art BLEU scores, surpassing previous models in both English-to-German and English-to-French translation tasks.; Demonstrated improved training efficiency, requiring significantly less time and computational resources than traditional models.; Successful application of the Transformer to English constituency parsing, showcasing its versatility beyond machine translation.	The paper does not provide detailed information on the preprocessing steps for the datasets, which could impact reproducibility.; Limited discussion on the potential biases in the datasets used for training and evaluation.; The focus on only two language pairs may restrict the generalizability of the findings to other languages or tasks.	Exploration of the Transformer's effectiveness on a wider range of NLP tasks beyond machine translation.; Investigation into the application of the Transformer architecture in low-resource language settings.; Development of improved training techniques or architectures that build upon the attention mechanisms introduced in this work.; Addressing the limitations of BLEU as an evaluation metric by incorporating additional qualitative assessments of translation quality.	2025-08-03 20:43:13.902538+00	2025-08-03 20:43:13.902538+00	The paper presents a novel and impactful architecture that significantly advances the field of natural language processing.; Methodological rigor is evident in the experimental design and thorough evaluation against state-of-the-art models.; Clear articulation of the theoretical underpinnings of the Transformer, enhancing understanding of its innovations.; Results demonstrate substantial improvements in both translation quality and training efficiency, indicating practical relevance.	Advancement of knowledge in sequence transduction through the introduction of the Transformer architecture.; Empirical evidence supporting the superiority of attention-based models over traditional recurrent and convolutional approaches.; Methodological innovations in neural network design that emphasize the power of self-attention mechanisms.; Practical applications for improving machine translation systems and a framework for future research in NLP.	The study primarily focuses on machine translation, which may limit the applicability of the findings to other NLP tasks.; The evaluation is based on BLEU scores, which, while widely used, may not capture all aspects of translation quality.; The model's performance on low-resource languages or domains is not addressed, potentially limiting its practical applications.
08cb5cf4-dd9f-4014-bb7b-c8aa938177c7	a6df804b-9eae-4e20-9dcd-f730c04d6058	This paper addresses the challenge of crowd counting, particularly the limitations of existing convolution-based attention networks in capturing global patterns. The authors propose the Fourier-Guided Attention (FGA) Network, which employs a dual-path architecture integrating Fast Fourier Transformations (FFT) for global feature extraction and traditional convolutions with channel-wise attention for local features. Experimental results demonstrate significant improvements in accuracy across several benchmark datasets, indicating FGA's potential to enhance crowd counting methodologies. The findings suggest broader implications for urban planning and public safety by improving the reliability of crowd estimation techniques.	This paper addresses the challenge of crowd counting, particularly the limitations of existing convolution-based attention networks in capturing global patterns. The authors propose the Fourier-Guided Attention (FGA) Network, which employs a dual-path architecture integrating Fast Fourier Transformations (FFT) for global feature extraction and traditional convolutions with channel-wise attention for local features. Experimental results demonstrate significant improvements in accuracy across several benchmark datasets, indicating FGA's potential to enhance crowd counting methodologies. The findings suggest broader implications for urban planning and public safety by improving the reliability of crowd estimation techniques.	{'experimental_design': 'The study employs a dual-path architecture in the FGA network, designed to process both global and local features effectively. One path utilizes FFT for full-scale global feature extraction, while the other employs traditional convolutions and channel-wise attention for semi-global and local features.', 'theoretical_framework': "The theoretical underpinning of the FGA approach is based on the integration of frequency domain analysis (via FFT) with spatial attention mechanisms to enhance the model's ability to capture diverse crowd patterns.", 'technical_approach': 'FGA integrates Fast Fourier Transformations for efficient global feature extraction and combines it with convolutional layers that utilize channel-wise attention to focus on local features. This hybrid approach aims to overcome the limitations of traditional convolutional networks in capturing long-range dependencies.', 'validation_strategy': "The performance of the FGA network is validated through experiments on benchmark datasets including ShanghaiTech-A, ShanghaiTech-B, UCF-CC-50, and JHU++. The evaluation metrics used are Mean-Squared-Error (MSE) and Mean-Absolute-Error (MAE), which provide a quantitative measure of the model's accuracy.", 'novel_methodological_contributions': 'The introduction of the FGA mechanism represents a novel methodological contribution by combining FFT with attention mechanisms, which has not been extensively explored in the context of crowd counting.'}	{'dataset_names': ['ShanghaiTech-A', 'ShanghaiTech-B', 'UCF-CC-50', 'JHU++'], 'sizes': 'Not clearly specified in the provided text', 'characteristics': 'These datasets contain images of varying crowd densities and scenes, which are essential for training and evaluating crowd counting models.', 'preprocessing_steps': 'Not clearly specified in the provided text', 'evaluation_metrics': ['Mean-Squared-Error (MSE)', 'Mean-Absolute-Error (MAE)'], 'data_limitations': 'Potential biases in the datasets related to scene diversity, lighting conditions, and occlusions may affect the generalizability of the findings.'}	Introduction of the Fourier-Guided Attention mechanism, enhancing the ability to capture multi-scale crowd patterns.; Demonstrated significant performance improvements in crowd counting accuracy across multiple benchmark datasets.; Effective integration of frequency domain analysis with spatial attention mechanisms, providing a novel approach to the problem.; Qualitative analysis using Grad-CAM heatmaps to illustrate the interpretability and effectiveness of the FGA in capturing crowd patterns.	The paper does not provide detailed information on the preprocessing steps applied to the datasets, which is crucial for reproducibility.; Limited discussion on the potential biases present in the datasets, which could impact the generalizability of the results.; The experimental design lacks a comparison with a wider range of baseline methods, which could strengthen the validation of the proposed approach.	Exploration of the FGA mechanism in other domains beyond crowd counting, such as object detection or scene understanding.; Investigation of alternative preprocessing techniques to enhance dataset diversity and robustness.; Development of hybrid models that combine FGA with other advanced neural network architectures.; Further validation on more diverse datasets to assess the generalizability of the proposed approach.	2025-08-03 20:43:39.761043+00	2025-08-03 20:43:39.761043+00	The methodological rigor of the dual-path architecture enhances the model's capability to capture both global and local features.; Comprehensive evaluation across multiple benchmark datasets demonstrates the effectiveness of the proposed approach.; Clarity of presentation and structured approach make the paper accessible to researchers in the field.	Advancement of crowd counting methodologies through the introduction of the FGA mechanism.; Provision of empirical evidence supporting the effectiveness of integrating frequency domain analysis with attention mechanisms.; Theoretical insights into the importance of capturing multi-scale information in crowd counting tasks.	The study is constrained by the specific datasets used, which may not represent all real-world crowd scenarios.; The focus on FFT and attention mechanisms may limit the exploration of other potentially effective methodologies.; Generalizability of the findings may be restricted due to the specific characteristics of the datasets employed.
902c1ebb-f612-4461-9116-ffdbf7426600	6300b3d8-1cdc-4a76-a5a9-4eaae00352e7	The paper presents Llama.lisp, a compiler framework designed to enhance performance portability for GPU programming through the use of device-agnostic intermediate representation languages (IRs) formulated as S-expressions. It introduces C-Lisp, a structured programming interface to LLVM IR, which leverages Lisp syntax to facilitate unique metaprogramming capabilities. Key findings demonstrate the effectiveness of this approach in simplifying the complexity of compiler development while maintaining high performance. The broader implications suggest that Llama.lisp could significantly streamline the GPU compiler ecosystem, potentially leading to more efficient AI algorithm implementations across diverse hardware architectures.	The paper presents Llama.lisp, a compiler framework designed to enhance performance portability for GPU programming through the use of device-agnostic intermediate representation languages (IRs) formulated as S-expressions. It introduces C-Lisp, a structured programming interface to LLVM IR, which leverages Lisp syntax to facilitate unique metaprogramming capabilities. Key findings demonstrate the effectiveness of this approach in simplifying the complexity of compiler development while maintaining high performance. The broader implications suggest that Llama.lisp could significantly streamline the GPU compiler ecosystem, potentially leading to more efficient AI algorithm implementations across diverse hardware architectures.	{'experimental_design': 'The study employs a multi-layered approach to compiler design, focusing on the development of C-Lisp as a structured interface to LLVM IR. The methodology emphasizes the use of S-expressions for representing both syntax and semantics, allowing for a clear mapping between high-level constructs and low-level operations.', 'theoretical_framework': 'The theoretical framework is grounded in the principles of Lisp and structured programming, which facilitate metaprogramming and abstraction in compiler design.', 'technical_approach': 'C-Lisp is implemented as a high-level interface that mirrors C language semantics while utilizing S-expressions for representation. This allows for a straightforward syntax that is both human-readable and machine-processable.', 'validation_strategy': 'Validation is achieved through the demonstration of FFI bindings as a practical application of the macro system within Llama.lisp, showcasing its capabilities in real-world scenarios.', 'novel_methodological_contributions': 'The paper contributes a novel approach to compiler design by integrating Lisp-inspired syntax with LLVM IR, enabling enhanced metaprogramming capabilities and simplifying the development process.'}	{'dataset_names': 'Not clearly specified in the provided text', 'sizes': 'Not clearly specified in the provided text', 'characteristics': 'The paper does not provide specific datasets but focuses on the compiler framework and its implementation.', 'preprocessing_steps': 'Not applicable as no datasets are mentioned.', 'evaluation_metrics': 'Not clearly specified in the provided text; however, performance metrics related to compiler efficiency and portability may be implied.', 'data_limitations_or_biases': 'Not applicable as no empirical data is presented.'}	Introduction of C-Lisp as a structured programming interface to LLVM IR, enhancing the usability of compiler frameworks.; Demonstration of the use of S-expressions for both syntax and semantic representation, facilitating easier compiler development.; Implementation of FFI bindings as a practical example of the macro system, showcasing the framework's capabilities.; Potential to improve performance portability across various hardware architectures, addressing fragmentation in the GPU compiler ecosystem.	Lack of empirical evaluation or case studies demonstrating the performance improvements of Llama.lisp compared to existing frameworks.; Insufficient discussion on the limitations of the proposed approach, particularly regarding its applicability to non-GPU architectures.; Theoretical gaps in addressing how C-Lisp handles complex programming constructs beyond basic operations.	Exploration of additional programming constructs and their representation in C-Lisp to enhance its applicability.; Development of benchmarking studies to quantitatively assess the performance of Llama.lisp against existing compiler frameworks.; Investigation into the integration of Llama.lisp with other programming languages and paradigms to broaden its usability.	2025-08-03 20:44:01.481536+00	2025-08-03 20:44:01.481536+00	The paper presents a novel approach to compiler design that leverages well-established programming principles.; Clear and concise presentation of the C-Lisp syntax and its correspondence with LLVM IR, aiding comprehension.; The proposed framework addresses a significant gap in the GPU compiler ecosystem, potentially leading to improved performance for AI algorithms.	Advancement of knowledge in compiler design through the introduction of Llama.lisp and C-Lisp.; Practical applications in GPU programming that could enhance the efficiency of AI algorithms.; Methodological innovations in using S-expressions for compiler representation, which may influence future compiler development.	The scope is limited to GPU programming and does not address other areas of compiler design.; The framework's generalizability to other programming paradigms or hardware architectures is not established.; No quantitative data or benchmarks are provided to substantiate claims of performance improvements.
60cea029-4698-4a37-84e3-e24e37209b78	23a1834f-a5b2-469c-a0f2-3658136a9344	This paper presents comprehensive lecture notes on neural network architectures, addressing the foundational concepts of machine learning, including supervised and unsupervised learning, optimization algorithms, and various neural network structures such as feedforward, convolutional, and recurrent networks. The approach taken is a synthesis of existing literature and educational resources, aimed at providing a cohesive theoretical background for practical programming sessions. Key findings include the clarification of complex topics like backpropagation, batch normalization, and transfer learning, which are essential for understanding modern neural network applications. The broader implication of this work lies in its potential to serve as an educational resource for researchers and practitioners in the field of deep learning, facilitating a better grasp of neural network design and implementation.	This paper presents comprehensive lecture notes on neural network architectures, addressing the foundational concepts of machine learning, including supervised and unsupervised learning, optimization algorithms, and various neural network structures such as feedforward, convolutional, and recurrent networks. The approach taken is a synthesis of existing literature and educational resources, aimed at providing a cohesive theoretical background for practical programming sessions. Key findings include the clarification of complex topics like backpropagation, batch normalization, and transfer learning, which are essential for understanding modern neural network applications. The broader implication of this work lies in its potential to serve as an educational resource for researchers and practitioners in the field of deep learning, facilitating a better grasp of neural network design and implementation.	{'experimental_design': 'The notes are structured as a series of educational modules, each focusing on specific aspects of neural networks, which allows for a systematic exploration of the subject matter.', 'theoretical_framework': 'The notes draw upon established theories in machine learning and neural networks, integrating insights from various academic sources to provide a well-rounded understanding of the topics.', 'technical_approach': 'The material covers a range of neural network architectures, including feedforward networks, convolutional networks, and recurrent networks, detailing their structures, functions, and applications.', 'validation_strategy': 'While the notes themselves do not present original experimental results, they reference established literature and educational practices to validate the information presented.', 'novel_methodological_contributions': 'The notes serve as a cohesive educational tool, synthesizing a wide array of sources into a structured format that aids in teaching complex concepts.'}	{'dataset_names': 'Not clearly specified in the provided text', 'sizes': 'Not clearly specified in the provided text', 'characteristics': 'Not clearly specified in the provided text', 'preprocessing_steps': 'Not clearly specified in the provided text', 'evaluation_metrics': 'Not clearly specified in the provided text', 'data_limitations': 'Not clearly specified in the provided text'}	Comprehensive coverage of fundamental concepts in neural networks, making it a valuable resource for both beginners and advanced learners.; Integration of various sources and educational practices, enhancing the clarity and cohesiveness of the material.; Detailed explanations of critical components such as backpropagation, batch normalization, and transfer learning, which are pivotal for practical applications.; Inclusion of diverse neural network architectures, providing a broad perspective on the field.	The notes do not present original research findings or experimental data, limiting their contribution to theoretical knowledge.; Lack of specific examples or case studies that could illustrate the practical application of the concepts discussed.; No clear identification of baseline models or comparative analyses that could contextualize the discussed architectures.	Exploration of novel neural network architectures that have emerged since the compilation of these notes.; Development of practical applications or case studies that could accompany the theoretical content to enhance understanding.; Investigation into the integration of optimal control perspectives in machine learning, as mentioned in the acknowledgments.	2025-08-03 20:44:30.042674+00	2025-08-03 20:44:30.042674+00	High methodological rigor in the synthesis of existing literature, providing a solid theoretical foundation.; Well-structured presentation that facilitates learning and comprehension of complex topics.; Clarity of explanations, making the material accessible to a wide audience, including those new to the field.	Advancement of educational resources in the field of neural networks, aiding in the dissemination of knowledge.; Provision of a comprehensive overview of neural network architectures, serving as a reference for researchers and practitioners.; Encouragement of further exploration and understanding of machine learning concepts through a well-organized framework.	The scope is primarily educational, focusing on theoretical aspects rather than empirical validation or novel research contributions.; Generalizability is limited as the notes are based on existing literature and do not introduce new experimental results.; Potential biases in the selection of sources may affect the comprehensiveness of the material.
c0b6e856-a0ca-4295-901f-02b77f5274fe	c32bdae7-2c1e-4987-9d3d-da9244c3ce68	This study addresses the prevalence and predictive factors of gastrointestinal (GI) symptoms in post-COVID-19 patients, utilizing machine learning techniques on data from 913 patients in Iraq. The authors identify significant predictive factors, including age, gender, disease severity, comorbidities, and duration of illness, with diarrhea being the most common symptom reported. The findings highlight the importance of monitoring GI symptoms in post-COVID-19 care and suggest that machine learning can enhance early identification and personalized interventions. This research contributes to the understanding of long-term COVID-19 effects on GI health and advocates for further exploration of underlying mechanisms.	This study addresses the prevalence and predictive factors of gastrointestinal (GI) symptoms in post-COVID-19 patients, utilizing machine learning techniques on data from 913 patients in Iraq. The authors identify significant predictive factors, including age, gender, disease severity, comorbidities, and duration of illness, with diarrhea being the most common symptom reported. The findings highlight the importance of monitoring GI symptoms in post-COVID-19 care and suggest that machine learning can enhance early identification and personalized interventions. This research contributes to the understanding of long-term COVID-19 effects on GI health and advocates for further exploration of underlying mechanisms.	The study employs a quantitative research design utilizing machine learning algorithms to analyze data collected from 913 post-COVID-19 patients. The theoretical framework is based on predictive modeling, where various demographic and clinical variables (age, gender, disease severity, comorbidities, and illness duration) are used as features in the model. Specific algorithms used for analysis are not detailed in the provided text, but the methodology suggests a robust validation strategy through statistical analysis of the predictive factors identified. The study may contribute novel insights into the application of machine learning in healthcare, particularly for symptom prediction.	{'dataset_name': 'Post-COVID-19 Patient Data', 'size': 913, 'characteristics': 'The dataset includes demographic information, clinical history, and reported GI symptoms from patients recovering from COVID-19 in Iraq.', 'preprocessing_steps': 'Not clearly specified in the provided text.', 'evaluation_metrics': 'Not clearly specified in the provided text.', 'data_limitations': 'The dataset is limited to a specific geographic region (Iraq), which may affect the generalizability of the findings. Additionally, potential biases in self-reported symptoms could influence the accuracy of the data.'}	Identification of diarrhea as the most prevalent GI symptom among post-COVID-19 patients.; Significant predictive factors for GI symptoms established, including age, gender, disease severity, comorbidities, and illness duration.; Demonstration of machine learning's utility in predicting health outcomes in post-COVID-19 care.; Emphasis on the need for targeted interventions to manage GI symptoms in recovering patients.	Lack of detailed information on the specific machine learning algorithms used, which limits reproducibility.; Insufficient baseline comparisons to other studies or control groups, which could strengthen the validity of the findings.; Potential biases in symptom reporting and lack of longitudinal data to assess changes over time.	Exploration of the underlying biological mechanisms contributing to GI symptoms in post-COVID-19 patients.; Development of more comprehensive machine learning models that incorporate additional variables and longitudinal data.; Investigation of targeted therapeutic interventions for managing GI symptoms in this patient population.; Expansion of the study to include diverse populations and settings to enhance generalizability.	2025-08-03 20:44:57.248718+00	2025-08-03 20:44:57.248718+00	Addresses a critical and emerging area of research concerning the long-term effects of COVID-19.; Utilizes machine learning as a novel approach to identify predictive factors, showcasing methodological innovation.; Provides empirical evidence on the prevalence of GI symptoms, which is often overlooked in COVID-19 research.; Clear articulation of the implications for clinical practice in post-COVID-19 care.	Advancement of knowledge regarding the gastrointestinal effects of COVID-19.; Practical applications in monitoring and managing GI symptoms in post-COVID-19 patients.; Theoretical insights into the role of machine learning in healthcare diagnostics and symptom prediction.; Empirical evidence supporting the need for comprehensive post-COVID-19 care strategies.	The study is geographically limited to Iraq, which may restrict the applicability of findings to other populations.; The cross-sectional nature of the study may not capture the dynamic changes in GI symptoms over time.; Data collection methods and preprocessing steps are not clearly outlined, raising concerns about data integrity and reliability.
a7b80e93-4c90-4822-94ab-07edd823de70	bb06552e-636d-4237-807e-2cc4c73338f4	This paper addresses the challenge of crowd counting in real-time video surveillance by proposing a Lightweight Crowd Density estimation model (LCDnet) that balances accuracy and computational efficiency. The authors introduce an innovative training method utilizing curriculum learning (CL) to enhance model performance. Experimental results demonstrate that LCDnet achieves competitive accuracy while significantly reducing inference time and memory requirements, making it suitable for deployment on edge devices with limited computing resources. The findings have broader implications for the development of efficient deep learning models in resource-constrained environments, particularly in surveillance applications.	This paper addresses the challenge of crowd counting in real-time video surveillance by proposing a Lightweight Crowd Density estimation model (LCDnet) that balances accuracy and computational efficiency. The authors introduce an innovative training method utilizing curriculum learning (CL) to enhance model performance. Experimental results demonstrate that LCDnet achieves competitive accuracy while significantly reducing inference time and memory requirements, making it suitable for deployment on edge devices with limited computing resources. The findings have broader implications for the development of efficient deep learning models in resource-constrained environments, particularly in surveillance applications.	{'experimental_design': 'The study employs a comparative approach, evaluating the proposed LCDnet against existing crowd counting models on benchmark datasets.', 'theoretical_framework': 'The research is grounded in the principles of convolutional neural networks (CNNs) and curriculum learning, aiming to optimize the trade-off between model complexity and performance.', 'technical_approach': 'LCDnet is designed as a lightweight CNN model, which is trained using curriculum learning to progressively introduce complexity in the training data, thereby improving learning efficiency.', 'validation_strategy': "The model's performance is validated through experiments on two benchmark datasets, DroneRGBT and CARPK, with results compared against established crowd counting models.", 'novel_methodological_contributions': 'The introduction of curriculum learning in the training process of a lightweight CNN for crowd density estimation represents a novel methodological contribution.'}	{'dataset_names': ['DroneRGBT', 'CARPK'], 'sizes': 'Not clearly specified in the provided text.', 'characteristics': 'Both datasets are designed for crowd counting and density estimation tasks, but specific characteristics such as resolution, diversity, and crowd density levels are not detailed.', 'preprocessing_steps': 'Not clearly specified in the provided text.', 'evaluation_metrics': 'Accuracy, inference time, and memory requirements are used as evaluation metrics.', 'data_limitations': 'Potential limitations include the representativeness of the datasets for real-world scenarios and the absence of detailed preprocessing information.'}	Introduction of LCDnet, a lightweight model that effectively reduces inference time and memory usage for crowd density estimation.; Utilization of curriculum learning to enhance the training process, leading to improved model performance.; Demonstration of competitive accuracy in crowd counting tasks compared to existing models, despite the lightweight design.; Potential for deployment in real-time video surveillance applications on edge devices.	The paper lacks detailed descriptions of the datasets, including sizes and preprocessing methods, which are critical for reproducibility.; Insufficient baseline comparisons with a wider range of existing models may limit the robustness of the claims regarding LCDnet's performance.; The theoretical justification for the choice of curriculum learning is not thoroughly discussed, which may leave questions about its necessity and effectiveness.	Exploration of additional datasets to validate the model's performance across diverse scenarios.; Investigation into alternative lightweight architectures or training methodologies to further enhance accuracy without compromising efficiency.; Potential applications of LCDnet in other domains, such as event monitoring or public safety, could be explored.; Further research into the integration of real-time feedback mechanisms to adapt the model dynamically based on environmental changes.	2025-08-03 21:56:59.460913+00	2025-08-03 21:56:59.460913+00	The proposed model demonstrates a strong balance between computational efficiency and accuracy, addressing a critical need in real-time applications.; The use of curriculum learning as a training strategy is innovative and may inspire further research in model training methodologies.; The clarity of presentation and structured approach to problem-solving enhances the paper's accessibility to researchers in the field.	Advancement of knowledge in lightweight crowd counting models suitable for real-time applications.; Practical implications for the deployment of deep learning models in resource-constrained environments.; Methodological innovation through the application of curriculum learning in the context of crowd density estimation.	The study may be limited by the specific datasets used, which may not encompass all real-world scenarios encountered in crowd counting.; The lightweight nature of the model may inherently restrict its accuracy in extremely dense crowd situations, which is not fully addressed.; Generalizability of the findings to other domains or types of crowd counting tasks remains uncertain.
2c62a3d6-b01f-4272-a529-f0b217dac42b	f9c43b41-6e01-4571-ae88-909821c25fed	This paper addresses the challenge of accurately analyzing highly congested scenes, specifically focusing on crowd counting and density map generation. The authors propose CSRNet, a novel architecture that combines a convolutional neural network (CNN) for feature extraction with a dilated CNN for enhanced spatial reception fields, thereby improving the model's ability to generate high-quality density maps. Experimental results demonstrate that CSRNet outperforms existing methods, achieving a 47.3% reduction in Mean Absolute Error (MAE) on the ShanghaiTech Part B dataset and a 15.4% improvement on the TRANCOS dataset for vehicle counting. The findings suggest that CSRNet can significantly enhance applications in crowd monitoring and safety management, highlighting its potential for real-world deployment in surveillance systems.	This paper addresses the challenge of accurately analyzing highly congested scenes, specifically focusing on crowd counting and density map generation. The authors propose CSRNet, a novel architecture that combines a convolutional neural network (CNN) for feature extraction with a dilated CNN for enhanced spatial reception fields, thereby improving the model's ability to generate high-quality density maps. Experimental results demonstrate that CSRNet outperforms existing methods, achieving a 47.3% reduction in Mean Absolute Error (MAE) on the ShanghaiTech Part B dataset and a 15.4% improvement on the TRANCOS dataset for vehicle counting. The findings suggest that CSRNet can significantly enhance applications in crowd monitoring and safety management, highlighting its potential for real-world deployment in surveillance systems.	CSRNet employs a two-component architecture: a standard CNN for initial feature extraction followed by a dilated CNN that utilizes dilated convolutions to expand the receptive field without increasing the number of parameters. This design allows for effective pixel-wise density estimation while maintaining spatial coherence in the output density maps. The model is trained end-to-end using standard backpropagation, and the authors emphasize its ease of training due to the absence of pooling layers, which can complicate gradient flow. Validation is performed against multiple datasets, demonstrating robustness across varying scene types and densities.	{'names': ['ShanghaiTech dataset', 'UCF CC50 dataset', 'WorldEXPO’10 dataset', 'UCSD dataset', 'TRANCOS dataset'], 'sizes': 'Not clearly specified in the provided text', 'characteristics': 'These datasets contain images of crowded scenes with varying densities and distributions, suitable for training and evaluating crowd counting models.', 'preprocessing_steps': 'Not clearly specified in the provided text', 'evaluation_metrics': 'Mean Absolute Error (MAE) is used as the primary metric for performance evaluation.', 'data_limitations': 'Potential biases in the datasets may arise from the specific contexts of the scenes captured, which could affect the generalizability of the model to other environments.'}	Introduction of CSRNet, a novel architecture that combines CNN and dilated CNN for improved density estimation in congested scenes.; Achieved state-of-the-art performance on multiple datasets, significantly reducing MAE compared to previous methods.; Demonstrated the applicability of CSRNet beyond crowd counting to other object counting tasks, such as vehicle detection.; Emphasized the model's ease of training and deployment in real-world surveillance applications.	The paper lacks detailed descriptions of the preprocessing steps applied to the datasets, which are crucial for reproducibility.; No comprehensive comparison with a wider range of baseline methods is provided, limiting the context of the claimed improvements.; The experimental results are primarily focused on a few datasets, which may not fully represent the diversity of real-world scenarios.	Exploration of CSRNet's architecture for other applications beyond crowd counting, such as traffic analysis or wildlife monitoring.; Investigating the integration of CSRNet with other modalities (e.g., temporal data) to enhance scene understanding.; Development of more robust training protocols to handle diverse and challenging real-world conditions.; Addressing the limitations related to dataset biases by incorporating more varied training data.	2025-08-03 22:03:37.529964+00	2025-08-03 22:03:37.529964+00	Methodological rigor in the design of CSRNet, which effectively addresses the challenges of congested scene analysis.; Clear demonstration of the model's performance improvements through empirical results on multiple datasets.; Theoretical soundness in the approach, leveraging dilated convolutions for enhanced spatial feature extraction.; Clarity of presentation, making the methodology and findings accessible to a broad audience.	Advancement of knowledge in the field of crowd counting and density estimation through the introduction of CSRNet.; Practical applications of the model in safety-critical environments, enhancing real-time monitoring capabilities.; Theoretical insights into the benefits of dilated convolutions for spatial feature extraction in congested scenes.; Empirical evidence supporting the effectiveness of CSRNet over existing methods, paving the way for future research.	The performance improvements are demonstrated on specific datasets, which may not generalize to all types of congested scenes.; The model's reliance on dilated convolutions may introduce challenges in scenarios with extreme variations in object density or scene complexity.; Potential biases in the datasets could affect the model's performance in different environmental contexts.
02605746-95aa-46fc-ac28-63efd0b834fe	3d228d2f-6e0b-438f-828a-432e7e8b7247	This paper addresses the critical issue of delayed diagnosis of diabetic retinopathy (DR) in rural areas due to a shortage of trained ophthalmologists and expensive diagnostic equipment. The authors propose a smartphone-based automated system utilizing an inception-based convolutional neural network (CNN) and a binary decision tree ensemble for the diagnosis and classification of DR. Key experimental findings indicate that the proposed system can provide an offline, point-of-care diagnosis, significantly improving accessibility for diabetic patients in remote locations. The broader implications suggest that such mobile solutions could enhance early detection and treatment of DR, potentially reducing the incidence of vision loss in underserved populations.	This paper addresses the critical issue of delayed diagnosis of diabetic retinopathy (DR) in rural areas due to a shortage of trained ophthalmologists and expensive diagnostic equipment. The authors propose a smartphone-based automated system utilizing an inception-based convolutional neural network (CNN) and a binary decision tree ensemble for the diagnosis and classification of DR. Key experimental findings indicate that the proposed system can provide an offline, point-of-care diagnosis, significantly improving accessibility for diabetic patients in remote locations. The broader implications suggest that such mobile solutions could enhance early detection and treatment of DR, potentially reducing the incidence of vision loss in underserved populations.	The methodology involves the development of a smartphone application that integrates an inception-based CNN for image classification and a binary decision tree ensemble for decision-making. The experimental design includes training the CNN on a dataset of fundus images to recognize various stages of diabetic retinopathy. The validation strategy likely includes cross-validation techniques to assess the model's performance, although specific details on the training process, hyperparameter tuning, and performance metrics are not provided in the text. The novelty lies in the deployment of this model on a mobile platform, allowing for offline diagnosis.	Not clearly specified in the provided text. The paper does not detail the specific dataset used for training the CNN, including its size, characteristics, and any preprocessing steps undertaken. Evaluation metrics for model performance are also not mentioned, which raises concerns about the robustness of the findings. Potential data limitations or biases that could affect conclusions are not discussed.	Proposes a novel smartphone application for the automated diagnosis of diabetic retinopathy, addressing accessibility issues in rural healthcare.; Utilizes an inception-based convolutional neural network combined with a binary decision tree ensemble, demonstrating an innovative approach to image classification.; Provides an offline diagnostic solution, enhancing the practicality of DR screening in areas with limited healthcare infrastructure.; Addresses a significant gap in the literature regarding point-of-care diagnostic tools for diabetic retinopathy.	Lack of detailed methodology regarding dataset characteristics and training processes limits reproducibility and assessment of the model's validity.; Insufficient baseline comparisons with existing DR diagnostic methods make it difficult to evaluate the performance improvements claimed.; The experimental design does not clearly outline the validation strategy or metrics used to assess model performance, raising questions about the reliability of the findings.; The paper does not address potential biases in the dataset or the generalizability of the results to diverse populations.	Future research could explore the integration of additional imaging modalities or advanced algorithms to improve diagnostic accuracy.; Investigating the application of the proposed system in real-world settings to validate its effectiveness and user-friendliness.; Extensions could include the development of a larger, more diverse dataset for training and testing the model to enhance its generalizability.; Theoretical questions regarding the interpretability of deep learning models in medical diagnosis could be addressed in subsequent studies.	2025-08-03 22:04:01.52908+00	2025-08-03 22:04:01.52908+00	Addresses a pressing public health issue with significant implications for early diagnosis and treatment of diabetic retinopathy.; Demonstrates methodological innovation by combining deep learning techniques with mobile technology for healthcare applications.; The clarity of presentation and structured approach to problem-solving enhance the paper's accessibility to a broad audience.; The focus on point-of-care solutions aligns with current trends in healthcare technology and accessibility.	Advances knowledge in the field of automated medical diagnosis, particularly for diabetic retinopathy.; Offers practical applications for mobile health technologies in underserved areas, potentially improving patient outcomes.; Provides theoretical insights into the capabilities of deep learning for image classification in medical contexts.; Introduces methodological innovations that could inspire further research and development in automated diagnostic systems.	The study's scope is limited to the development of a mobile application without extensive field testing or real-world validation.; Data constraints are evident due to the lack of information on the dataset used, which may affect the generalizability of the findings.; Methodological boundaries include the reliance on a specific neural network architecture, which may not be optimal for all types of fundus images.; The inherent restrictions of mobile applications in terms of processing power and image quality may limit diagnostic accuracy.
dd8f2067-4627-473a-991d-2b9cc11c895b	135598cf-16f6-46c7-948a-db8275485a68	This paper addresses the critical issue of early detection of Diabetic Retinopathy (DR), a condition that poses a significant risk of vision loss for millions globally. The authors propose a novel approach utilizing a modified DenseNet121 deep learning architecture trained on the APTOS 2019 dataset to enhance the accuracy of DR grading. Key experimental findings indicate that their method achieves a remarkable accuracy of 96.51% for multi-label classification and 94.44% for single-class classification, alongside strong precision and recall metrics. The broader implications suggest that this automated grading system could significantly improve early detection rates, thereby reducing the incidence of vision loss due to DR.	This paper addresses the critical issue of early detection of Diabetic Retinopathy (DR), a condition that poses a significant risk of vision loss for millions globally. The authors propose a novel approach utilizing a modified DenseNet121 deep learning architecture trained on the APTOS 2019 dataset to enhance the accuracy of DR grading. Key experimental findings indicate that their method achieves a remarkable accuracy of 96.51% for multi-label classification and 94.44% for single-class classification, alongside strong precision and recall metrics. The broader implications suggest that this automated grading system could significantly improve early detection rates, thereby reducing the incidence of vision loss due to DR.	{'experimental_design': 'The study employs a deep learning framework, specifically a modified DenseNet121 architecture, to automate the grading of Diabetic Retinopathy from fundus images. The design includes various modifications to the pre-trained model to enhance its performance.', 'theoretical_framework': "The theoretical basis rests on convolutional neural networks (CNNs) and transfer learning, leveraging the DenseNet architecture's ability to capture intricate features in image data.", 'technical_approach': "The authors utilize transfer learning with DenseNet121, which is known for its efficiency in handling image classification tasks. The modifications made to the architecture are not explicitly detailed in the abstract but are crucial for understanding the model's performance.", 'validation_strategy': 'The performance of the proposed model is validated through metrics such as accuracy, precision, recall, F1-score, and quadratic weighted kappa, providing a comprehensive evaluation of its effectiveness.', 'novel_methodological_contributions': 'The paper presents a modified version of DenseNet121 specifically tailored for the task of DR grading, which may offer insights into the application of deep learning in medical image analysis.'}	{'dataset_names': 'APTOS 2019 dataset', 'sizes': 'Not clearly specified in the provided text', 'characteristics': 'The dataset consists of fundus photography images categorized into severity levels of Diabetic Retinopathy: Normal, Mild, Moderate, Severe, and Proliferative.', 'preprocessing_steps': 'Not clearly specified in the provided text', 'evaluation_metrics': "Accuracy, precision, recall, F1-score, and quadratic weighted kappa are used to evaluate the model's performance.", 'data_limitations': 'Potential biases in the dataset may arise from the selection of images, which could affect the generalizability of the findings.'}	Achieved 96.51% accuracy in multi-label classification of Diabetic Retinopathy severity.; Demonstrated strong performance metrics including precision (86%), recall (87%), and F1-score (86%).; Utilized a modified DenseNet121 architecture, contributing to the body of knowledge on deep learning applications in medical imaging.; Proposed an efficient model that balances accuracy with computational efficiency.	The modifications made to the DenseNet121 architecture are not sufficiently detailed, limiting reproducibility.; The dataset size and specific preprocessing steps are not provided, which raises concerns about the robustness of the findings.; No comparison with other state-of-the-art methods is detailed, which may understate the significance of the reported performance improvements.	Exploration of additional datasets to validate the model's performance across diverse populations.; Investigation into the impact of different preprocessing techniques on model accuracy.; Extension of the model to include other eye diseases or conditions for broader applicability.; Development of a user-friendly interface for clinical integration of the automated grading system.	2025-08-03 22:04:29.127364+00	2025-08-03 22:04:29.127364+00	The paper addresses a significant public health issue with potential for real-world impact.; The methodological approach is grounded in established deep learning techniques, providing a solid foundation for the research.; The results indicate a high level of accuracy and reliability, suggesting practical applications in clinical settings.; The clarity of presentation and structured approach enhances the accessibility of the findings.	Advancement of automated diagnostic techniques for Diabetic Retinopathy.; Empirical evidence supporting the effectiveness of deep learning in medical image analysis.; Methodological innovations through the adaptation of DenseNet121 for specific medical applications.; Potential for practical applications in improving early detection and treatment of Diabetic Retinopathy.	The study's findings may be limited by the specific characteristics of the APTOS 2019 dataset, which may not represent the broader population.; The lack of detailed methodology regarding data preprocessing and model modifications restricts the ability to replicate the study.; Generalizability of results may be constrained by the dataset's inherent biases and the specific conditions under which the model was trained.
6c070420-58c1-477c-a8fc-a5f9bf18b7ad	b3251a67-101b-40ab-a1e7-551c18ccbecb	This paper addresses the challenge of distributional shifts in automated diabetic retinopathy (DR) screening, where deep learning models struggle with classifying images that deviate from their training distribution. The authors propose a novel framework based on Dirichlet Prior Networks, which integrates an out-of-distribution (OOD) detection model with a DR classification model to enhance generalizability by identifying OOD images. Experimental results demonstrate that the proposed approach effectively filters out non-retina images and accurately identifies shifted retina images requiring human intervention. These findings have significant implications for improving the reliability of automated DR screening systems in real-world applications.	This paper addresses the challenge of distributional shifts in automated diabetic retinopathy (DR) screening, where deep learning models struggle with classifying images that deviate from their training distribution. The authors propose a novel framework based on Dirichlet Prior Networks, which integrates an out-of-distribution (OOD) detection model with a DR classification model to enhance generalizability by identifying OOD images. Experimental results demonstrate that the proposed approach effectively filters out non-retina images and accurately identifies shifted retina images requiring human intervention. These findings have significant implications for improving the reliability of automated DR screening systems in real-world applications.	The methodology involves the development of a Dirichlet Prior Network-based framework that combines an OOD detection model with a DR classification model. The framework is designed to enhance the model's ability to generalize across different distributions by effectively identifying images that are OOD. The experimental design includes training the model on a set of retina images with standard preprocessing techniques such as image normalization and data augmentation. The validation strategy includes evaluating the model's performance on real-world datasets to assess its accuracy in detecting referable DR and distinguishing between in-distribution and OOD images. The paper introduces a novel approach to predictive uncertainty estimation by leveraging the Dirichlet Prior Network, which is not commonly used in this context.	The paper utilizes real-world datasets for training and evaluation, although specific dataset names and sizes are not provided in the text. The characteristics of the datasets include a mix of retina images from various sources, which may exhibit distributional differences. Preprocessing steps mentioned include image normalization and data augmentation to improve generalization. Evaluation metrics for assessing model performance are not explicitly detailed, and potential data limitations or biases, such as the representation of different demographic groups or variations in image quality, are not discussed.	Introduction of a Dirichlet Prior Network-based framework that integrates OOD detection with DR classification.; Demonstration of improved generalizability in DR screening models by effectively identifying OOD images.; Experimental validation showing the framework's capability to eliminate non-retina images and identify shifted retina images for human intervention.; Contribution to the understanding of predictive uncertainty in deep learning models for medical image classification.	Lack of detailed information regarding the datasets used, including names, sizes, and specific characteristics.; Insufficient discussion on the evaluation metrics employed to assess the model's performance.; Potential methodological flaws in the experimental design due to the absence of clear baselines for comparison.; Limited exploration of the implications of model uncertainty and data uncertainty on the results.	Exploration of additional datasets to validate the framework's effectiveness across diverse populations and imaging conditions.; Investigation of alternative OOD detection techniques that could complement or enhance the proposed framework.; Development of strategies to address the identified limitations, such as improving dataset diversity and representation.; Theoretical inquiries into the nature of predictive uncertainty in deep learning models and its implications for clinical practice.	2025-08-03 21:59:20.798152+00	2025-08-03 22:05:19.243086+00	Methodological rigor in the development of a novel framework that addresses a critical issue in medical image classification.; Quality of experimental design, with a clear focus on real-world applicability and the need for human intervention.; Theoretical soundness in linking predictive uncertainty to practical challenges in DR screening.; Clarity of presentation, making complex concepts accessible to a broad audience.	Advancement of knowledge in the field of automated diabetic retinopathy screening through the introduction of a new framework.; Practical applications of the proposed method in improving the reliability of DR screening systems.; Theoretical insights into the nature of distributional shifts and their impact on deep learning model performance.; Methodological innovations that pave the way for future research in predictive uncertainty and OOD detection.	Scope limitations due to the focus on specific types of distributional shifts without exploring other potential factors affecting model performance.; Data constraints related to the lack of transparency regarding dataset diversity and representation.; Methodological boundaries stemming from the reliance on a single framework without exploring alternative approaches.; Generalizability limits of the findings to other medical imaging contexts or different populations.
a4ede151-b547-43de-af4a-d3939f686c1d	d28b3211-9f93-4271-8d5b-680807b486e0	This paper addresses the challenge of detecting Diabetic Retinopathy (DR), a leading cause of vision loss among diabetic patients, through an ensemble machine learning approach. The authors propose a novel framework that combines multiple well-known classification algorithms to enhance diagnostic accuracy, achieving notable results with accuracy rates of 70.7% and 75.1% on selected subdatasets derived from the Messidor dataset. The findings suggest that using a reduced feature set can simplify the classification process while maintaining high accuracy, which has significant implications for the development of cost-effective and accessible DR detection systems. This work contributes to the field by providing a promising methodology for improving automated medical diagnostics in ophthalmology.	This paper addresses the challenge of detecting Diabetic Retinopathy (DR), a leading cause of vision loss among diabetic patients, through an ensemble machine learning approach. The authors propose a novel framework that combines multiple well-known classification algorithms to enhance diagnostic accuracy, achieving notable results with accuracy rates of 70.7% and 75.1% on selected subdatasets derived from the Messidor dataset. The findings suggest that using a reduced feature set can simplify the classification process while maintaining high accuracy, which has significant implications for the development of cost-effective and accessible DR detection systems. This work contributes to the field by providing a promising methodology for improving automated medical diagnostics in ophthalmology.	{'experimental_design': 'The study employs an ensemble learning strategy that integrates various classification algorithms to improve the detection of DR. The authors utilize a systematic approach to feature selection, generating subdatasets based on the top features identified through InfoGainEval and WrapperSubsetEval methods.', 'theoretical_framework': 'The theoretical basis for the study rests on the principles of ensemble learning, which leverages the strengths of multiple models to enhance predictive performance and robustness.', 'technical_approach': 'The paper details the implementation of ensemble methods, although specific algorithms used in the ensemble are not clearly specified in the provided text. The focus is on combining classifiers to achieve superior accuracy.', 'validation_strategy': 'The validation of the proposed model is conducted through accuracy metrics on the generated subdatasets, comparing results against the original dataset to demonstrate improvements.', 'novel_methodological_contributions': 'The creation of subdatasets based on feature selection techniques represents a methodological innovation aimed at reducing complexity while maintaining classification accuracy.'}	{'dataset_names': 'Messidor dataset', 'sizes': 'Not clearly specified in the provided text', 'characteristics': 'The Messidor dataset is known for containing retinal images annotated for DR, but specific characteristics such as image resolution or number of classes are not detailed.', 'preprocessing_steps': 'Not clearly specified in the provided text', 'evaluation_metrics': 'Accuracy rates are used as the primary evaluation metric, with specific results reported for different configurations.', 'data_limitations': 'The authors mention limited reliable datasets for DR detection, which may affect the generalizability and robustness of their findings.'}	Proposed an ensemble-based learning strategy that merges multiple classification algorithms for improved DR detection.; Achieved significant accuracy improvements using reduced feature sets, indicating a less complex classification process.; Demonstrated the potential for automated DR detection systems to enhance accessibility and efficiency in clinical settings.; Provided empirical evidence supporting the effectiveness of feature selection techniques in machine learning applications for medical diagnostics.	Lacks clarity on the specific algorithms used in the ensemble, which limits reproducibility and understanding of the approach.; The dataset size and characteristics are not sufficiently detailed, which raises concerns about the robustness of the findings.; No mention of baseline comparisons with existing state-of-the-art methods, making it difficult to assess the relative performance of the proposed approach.; Limited discussion on potential overfitting issues related to the ensemble method and feature selection.	Exploration of additional ensemble techniques or hybrid models that could further enhance detection accuracy.; Investigation into the applicability of the proposed approach on larger and more diverse datasets.; Development of real-time DR detection systems that integrate the proposed methodology into clinical workflows.; Examination of the impact of additional features or data modalities (e.g., patient demographics) on classification performance.	2025-08-03 22:04:56.156449+00	2025-08-03 22:04:56.156449+00	Addresses a critical healthcare issue with significant implications for patient outcomes.; Demonstrates methodological rigor through the use of ensemble learning and feature selection.; Presents clear empirical results that support the proposed approach and its effectiveness.; Contributes to the ongoing discourse on automated medical diagnostics, particularly in ophthalmology.	Advances knowledge in the field of automated diabetic retinopathy detection through innovative methodological approaches.; Provides practical insights for developing cost-effective diagnostic tools that could be implemented in resource-limited settings.; Offers empirical evidence that supports the use of ensemble learning in medical image analysis.; Highlights the importance of feature selection in improving machine learning model performance in healthcare applications.	The study is constrained by the availability of reliable datasets for DR, which may limit the applicability of the findings.; Generalizability may be affected due to the specific dataset used and the lack of diverse data sources.; The methodology may not be applicable to all forms of DR or other medical conditions without further validation.; The paper does not address potential biases in the dataset that could influence the results.
\.


--
-- Data for Name: document_sessions; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.document_sessions (id, file_id, session_token, crdt_state, crdt_type, active_users, last_activity, autosave_pending, created_at, expires_at) FROM stdin;
\.


--
-- Data for Name: email_verification_tokens; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.email_verification_tokens (id, user_id, email, token, expires_at, verified_at, created_at) FROM stdin;
e9f36ffd-626b-4a20-9067-9f4a3d981df2	ff40fb7e-b5b8-436a-b16f-cc4a31146ff5	chaudhuri.yash@gmail.com	yzgCVPBodUvzysf04KfxsgIE-2Zx3-Keuky1aNrC8b4	2025-08-04 19:32:01.238475+00	2025-08-03 19:37:01.731952+00	2025-08-03 19:32:00.907162+00
\.


--
-- Data for Name: feature_analytics; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.feature_analytics (id, feature_name, feature_category, date, total_uses, unique_users, avg_duration_seconds, success_rate, created_at) FROM stdin;
\.


--
-- Data for Name: file_uploads; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.file_uploads (id, user_id, original_filename, stored_filename, file_path, file_size, mime_type, checksum, uploaded_at) FROM stdin;
\.


--
-- Data for Name: git_repositories; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.git_repositories (id, project_id, repo_path, repo_url, default_branch_id, last_commit_hash, initialized, created_at, updated_at) FROM stdin;
be31d49c-1e9c-401d-98a9-abedc7c1429a	36eae63b-2fc6-4543-acab-2197c8a3cff6	/home/ec2-user/ResXiv_V2/backend/repositories/test-run_36eae63b	\N	d1b97253-d447-4949-a01e-850be870a414	\N	t	2025-08-03 19:49:53.96827+00	2025-08-03 19:49:53.96827+00
c69b03b9-aeff-498d-88ee-dfb093a5c43b	28f846fd-e8f5-48dd-814e-526854578e3a	/home/ec2-user/ResXiv_V2/backend/repositories/test-run_28f846fd	\N	5eed7bd3-d185-477c-8303-a13f6e5352f6	\N	t	2025-08-03 20:24:04.635136+00	2025-08-03 20:24:04.635136+00
2d6d99eb-0f94-4466-bb08-67843b452268	7b2f8acd-a112-45f7-b166-3ba25f95e669	/home/ec2-user/ResXiv_V2/backend/repositories/test-run_7b2f8acd	\N	d92cd427-0790-40e5-932e-807ca28fc8f7	\N	t	2025-08-03 20:39:01.347069+00	2025-08-03 20:39:01.347069+00
\.


--
-- Data for Name: graphs; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.graphs (id, project_id, graph_path, graph_type, metadata, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: highlights; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.highlights (id, user_id, paper_id, project_id, name, is_public, start_pos, end_pos, content, color, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: invitation_reminders; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.invitation_reminders (id, invitation_id, sent_at, reminder_count) FROM stdin;
\.


--
-- Data for Name: latex_comments; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.latex_comments (id, project_id, commit_hash, user_id, content, line_number, file_path, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: latex_commits; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.latex_commits (id, project_id, user_id, commit_hash, message, parent_commit, branch, created_at) FROM stdin;
\.


--
-- Data for Name: latex_conflicts; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.latex_conflicts (id, project_id, base_commit, target_commit, conflict_file, conflict_section, resolution, resolved_by, created_at, resolved_at, resolved) FROM stdin;
\.


--
-- Data for Name: latex_files; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.latex_files (id, project_id, branch_id, file_path, file_name, file_type, file_size, encoding, created_by, created_at, updated_at, last_modified_by, deleted_at) FROM stdin;
\.


--
-- Data for Name: latex_snapshots; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.latex_snapshots (id, project_id, commit_hash, label, description, user_id, created_at) FROM stdin;
\.


--
-- Data for Name: notes; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.notes (id, user_id, paper_id, project_id, name, is_public, text, "position", created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: paper_embeddings; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.paper_embeddings (id, paper_id, embedding_model, title_embedding, abstract_embedding, combined_embedding, embedding_created_at, embedding_updated_at, embedding, source_text, model_name, processing_status, created_at, updated_at, error_message, model_version, embedding_metadata) FROM stdin;
fc30b3ce-d976-40e8-8fab-adf19e013d27	00b2848f-d0b0-4623-a321-bc74539f9703	all-MiniLM-L6-v2	\N	\N	\N	2025-08-03 20:43:13.912864+00	2025-08-03 20:43:13.912864+00	[-0.10995,-0.112957,0.03232,-0.021363,0.049848,0.047703,-0.069967,0.005118,0.135309,-0.021667,0.013588,-0.049098,-0.050451,0.041129,-0.081589,0.00439,0.015915,0.049309,-0.06033,-0.079092,0.022145,0.063751,0.015367,0.005128,-0.002969,-0.006836,-0.063363,-0.043067,-0.001551,0.026896,0.020804,-0.028446,7.6e-05,0.095262,-0.057908,0.060835,-0.063352,-0.011928,0.029638,-0.036711,0.028353,-0.026874,-0.013988,0.030629,0.149389,0.046927,-0.003266,-0.010565,-0.012788,0.010255,-0.094856,0.084215,0.017542,0.110733,-0.004727,-0.01282,-0.017632,-0.025532,-0.004111,-0.074925,-0.075396,-0.042836,-0.038404,-0.104828,-0.005959,0.000571,0.007012,0.008203,-0.076084,0.043249,0.012866,0.07959,-0.033344,0.015774,-0.007384,0.028074,0.071736,-0.006176,0.01874,-0.094905,0.065857,0.034627,0.12157,-0.008665,0.040164,-0.048197,-0.017448,0.045578,-0.003898,0.042403,-0.024859,-0.0873,0.1167,-0.055852,0.052757,0.073519,-0.029609,0.006532,0.002766,0.041978,0.043168,0.01419,0.036337,-0.114469,-0.02592,-0.002235,0.057876,0.041055,0.035986,-0.072077,-0.027908,0.007244,0.006568,-0.038158,0.043163,-0.062545,-0.043482,-0.007166,0.04291,-0.000153,0.00878,0.035098,-0.057965,0.065913,0.008856,-0.040884,-0.042181,0,0.016476,0.040708,0.006527,-0.014914,0.018049,0.025825,-0.051865,0.017611,-0.043257,-0.027381,-0.1064,-0.027231,-0.071901,0.063502,-0.01579,0.008308,0.001402,0.027593,-0.014385,-0.042266,-0.009905,0.006529,0.008501,-0.00165,-0.015532,0.012804,-0.012499,-0.088899,-0.076844,-0.01201,-0.128153,0.046385,-0.018014,-0.023998,0.032886,-0.102407,0.030584,-0.046382,0.043835,-0.048371,-0.04001,0.116384,-0.063294,0.051922,-0.020651,0.002601,0.034238,0.009493,0.040201,-0.041368,0.054816,0.012586,-0.072731,-0.130233,0.050564,0.067179,0.040027,0.084394,0.083697,0.059872,0.023923,0.04686,-0.005522,0.119285,0.105142,0.018257,-0.10975,0.055589,0.038874,-0.005414,0.0225,0.009757,-0.019354,-0.011874,0.047623,0.020969,0.003612,-0.080272,-0.086027,0.041929,-0.04325,0.010637,-0.028839,-0.028408,-0.071021,0.039869,0.107184,-0.017933,-0.002172,-0.021262,0.045861,0.007569,0.036315,-1e-05,-0.00993,-0,-0.009519,0.040146,-0.03056,0.041378,-0.07945,-0.049136,-0.014859,0.026699,-0.005534,0.002914,0.025404,-0.120898,0.061483,-0.001856,0.038047,-0.078803,0.005434,0.014877,-0.05219,0.039115,0.045775,0.11097,-0.104466,-0.035457,-0.015025,0.007208,-0.041789,0.134903,-0.015631,-0.024501,-0.086119,0.070122,0.004358,-0.006579,-0.044639,0.082398,0.02808,-0.043345,-0.061482,0.039192,0.094038,-0.002647,-0.026798,0.045444,-0.053961,-0.048785,-0.114061,0.049292,-0.019235,0.042592,0.00028,0.011676,-0.108304,-0.040099,-0.001241,-0.010537,-0.026683,-0.037928,-0.006321,-0.061162,-0.073722,-0.004489,0.014191,-0.025665,0.056544,0.006285,0.020831,-0.019859,0.08525,-0.023418,0.017861,-0.042642,0.064324,0.043172,0.040311,-0.049216,-0.020596,-0.0105,0.014194,-0.045593,-0.067689,-0.05013,0.012209,0.025158,0.023575,0.038575,0.058602,0.01804,0.039417,0.01036,-0.022823,-0.038311,0.023169,0.063398,-0.044233,-0,-0.0535,-0.055968,-0.000226,0.001748,0.054055,-0.106048,0.009738,0.027729,-0.040634,-0.014792,0.01508,0.025259,-0.053357,-0.016108,-0.029515,0.10971,0.094564,-0.034513,0.021334,-0.011674,0.050858,0.048496,-0.006011,0.045048,0.016228,-0.038177,-0.11174,0.039352,0.011724,-0.033844,0.049277,0.002304,0.00137,-0.063545,0.031328,0.02734,0.034388,-0.007613,-0.013137,-0.026529,0.079852,0.032547,-0.064788,0.037325,-0.03451,-0.058636,-0.002356,-0.080029,0.048632,-0.042794,0.090249,-0.066284,0.056421,0.024337,0.006334,-0.006572,0.052239,-0.031433,-0.005072,0.063828,0.129003,0.075951,-0.026528,-0.056026]	Provided proper attribution is provided, Google hereby grants permission to\nreproduce the tables and figures in this paper solely for use in journalistic or\nscholarly works.\nAttention Is All You Need\nAshish Vaswani∗\nGoogle Brain\navaswani@google.comNoam Shazeer∗\nGoogle Brain\nnoam@google.comNiki Parmar∗\nGoogle Research\nnikip@google.comJakob Uszkoreit∗\nGoogle Research\nusz@google.com\nLlion Jones∗\nGoogle Research\nllion@google.comAidan N. Gomez∗ †\nUniversity of Toronto\naidan@cs.toronto.eduŁukasz Kaiser∗\nGoogle Brain\nlukaszkaiser@google.com\nIllia Polosukhin∗ ‡\nillia.polosukhin@gmail.com\nAbstract\nThe dominant sequence transduction models are based on complex recurrent or\nconvolutional neural networks that include an encoder and a decoder. The best\nperforming models also connect the encoder and decoder through an attention\nmechanism. We propose a new simple network architecture, the Transformer,\nbased solely on attention mechanisms, dispensing with recurrence and convolutions\nentirely. Experiments on two machine translation tasks show these models to\nbe superior in quality while being more parallelizable and requiring significantly\nless time to train. Our model achieves 28.4 BLEU on the WMT 2014 English-\nto-German translation task, improving over the existing best results, including\nensembles, by over 2 BLEU. On the WMT 2014 English-to-French translation task,\nour model establishes a new single-model state-of-the-art BLEU score of 41.8 after\ntraining for 3.5 days on eight GPUs, a small fraction of the training costs of the\nbest models from the literature. We show that the Transformer generalizes well to\nother tasks by applying it successfully to English constituency parsing both with\nlarge and limited training data.\n∗Equal contribution. Listing order is random. Jakob proposed replacing RNNs with self-attention and started\nthe effort to evaluate this idea. Ashish, with Illia, designed and implemented the first Transformer models and\nhas been crucially involved in every aspect of this work. Noam proposed scaled dot-product attention, multi-head\nattention and the parameter-free position representation and became the other person involved in nearly every\ndetail. Niki designed, implemented, tuned and evaluated countless model variants in our original codebase and\ntensor2tensor. Llion also experimented with novel model variants, was responsible for our initial codebase, and\nefficient inference and visualizations. Lukasz and Aidan spent countless long days designing various parts of and\nimplementing tensor2tensor, replacing our earlier codebase, greatly improving results and massively accelerating\nour research.\n†Work performed while at Google Brain.\n‡Work performed while at Google Research.\n31st Conference on Neural Information Processing Systems (NIPS 2017), Long Beach, CA, USA.arXiv:1706.03762v7  [cs.CL]  2 Aug 2023\n\n1 Introduction\nRecurrent neural networks, long short-term memory [ 13] and gated recurrent [ 7] neural networks\nin particular, have been firmly established as state of the art approaches in sequence modeling and\ntransduction problems such as language modeling and machine translation [ 35,2,5]. Numerous\nefforts have since continued to push the boundaries of recurrent language models and encoder-decoder\narchitectures [38, 24, 15].\nRecurrent models typically factor computation along the symbol positions of the input and output\nsequences. Aligning the positions to steps in computation time, they generate a sequence of hidden\nstates ht, as a function of the previous hidden state ht−1and the input for position t. This inherently\nsequential nature precludes parallelization within training examples, which becomes critical at longer\nsequence lengths, as memory constraints limit batching across examples. Recent work has achieved\nsignificant improvements in computational efficiency through factorization tricks [ 21] and conditional\ncomputation [ 32], while also improving model performance in case of the latter. The fundamental\nconstraint of sequential computation, however, remains.\nAttention mechanisms have become an integral part of compelling sequence modeling and transduc-\ntion models in various tasks, allowing modeling of dependencies without regard to their distance in\nthe input or output sequences [ 2,19]. In all but a few cases [ 27], however, such attention mechanisms\nare used in conjunction with a recurrent network.\nIn this work we propose the Transformer, a model architecture eschewing recurrence and instead\nrelying entirely on an attention mechanism to draw global dependencies between input and output.\nThe Transformer allows for significantly more parallelization and can reach a new state of the art in\ntranslation quality after being trained for as little as twelve hours on eight P100 GPUs.\n2 Background\nThe goal of reducing sequential computation also forms the foundation of the Extended Neural GPU\n[16], ByteNet [ 18] and ConvS2S [ 9], all of which use convolutional neural networks as basic building\nblock, computing hidden representations in parallel for all input and output positions. In these models,\nthe number of operations required to relate signals from two arbitrary input or output positions grows\nin the distance between positions, linearly for ConvS2S and logarithmically for ByteNet. This makes\nit more difficult to learn dependencies between distant positions [ 12]. In the Transformer this is\nreduced to a constant number of operations, albeit at the cost of reduced effective resolution due\nto averaging attention-weighted positions, an effect we counteract with Multi-Head Attention as\ndescribed in section 3.2.\nSelf-attention, sometimes called intra-attention is an attention mechanism relating different positions\nof a single sequence in order to compute a representation of the sequence. Self-attention has been\nused successfully in a variety of tasks including reading comprehension, abstractive summarization,\ntextual entailment and learning task-independent sentence representations [4, 27, 28, 22].\nEnd-to-end memory networks are based on a recurrent attention mechanism instead of sequence-\naligned recurrence and have been shown to perform well on simple-language question answering and\nlanguage modeling tasks [34].\nTo the best of our knowledge, however, the Transformer is the first transduction model relying\nentirely on self-attention to compute representations of its input and output without using sequence-\naligned RNNs or convolution. In the following sections, we will describe the Transformer, motivate\nself-attention and discuss its advantages over models such as [17, 18] and [9].\n3 Model Architecture\nMost competitive neural sequence transduction models have an encoder-decoder structure [ 5,2,35].\nHere, the encoder maps an input sequence of symbol representations (x1, ..., x n)to a sequence\nof continuous representations z= (z1, ..., z n). Given z, the decoder then generates an output\nsequence (y1, ..., y m)of symbols one element at a time. At each step the model is auto-regressive\n[10], consuming the previously generated symbols as additional input when generating the next.\n2\n\nFigure 1: The Transformer - model architecture.\nThe Transformer follows this overall architecture using stacked self-attention and point-wise, fully\nconnected layers for both the encoder and decoder, shown in the left and right halves of Figure 1,\nrespectively.\n3.1 Encoder and Decoder Stacks\nEncoder: The encoder is composed of a stack of N= 6 identical layers. Each layer has two\nsub-layers. The first is a multi-head self-attention mechanism, and the second is a simple, position-\nwise fully connected feed-forward network. We employ a residual connection [ 11] around each of\nthe two sub-layers, followed by layer normalization [ 1]. That is, the output of each sub-layer is\nLayerNorm( x+ Sublayer( x)), where Sublayer( x)is the function implemented by the sub-layer\nitself. To facilitate these residual connections, all sub-layers in the model, as well as the embedding\nlayers, ...	all-MiniLM-L6-v2	completed	2025-08-03 20:43:13.912864+00	2025-08-03 20:43:13.912864+00	\N	\N	\N
d617da1b-72f1-4ef5-bb81-849bfb80c7da	a6df804b-9eae-4e20-9dcd-f730c04d6058	all-MiniLM-L6-v2	\N	\N	\N	2025-08-03 20:43:39.769098+00	2025-08-03 20:43:39.769098+00	[0.04903,-0.082521,0.000402,0.03775,0.082029,0.0826,-0.03613,-0.031972,0.063624,-0.047426,-0.023827,-0.053082,-0.062333,0.04266,-0.000277,-0.060336,0.018863,0.033778,-0.077386,-0.06216,0.045495,-0.02163,0.018335,-0.02092,-0.021392,-0.021866,-0.032805,-0.039891,0.027892,0.004744,0.063901,0.087577,0.07114,0.108585,-0.067575,0.061629,-0.061343,0.008439,-0.017863,0.015173,0.020571,0.002817,-0.014208,-0.015665,0.055872,0.051748,-0.011444,0.002249,0.055018,0.006441,0.027237,0.028631,-0.01945,0.043236,0.034524,-0.003117,0.021626,-0.044279,0.017408,-0.015575,0.005575,-0.038505,-0.035954,-0.046618,-0.002507,-0.024392,-0.010816,-0.037557,0.040496,-0.027347,-0.0069,0.069401,0.099334,-0.005705,0.060218,0.023006,-0.081244,0.003514,0.042907,-0.073669,0.115302,-0.058068,0.137094,-0.026128,0.16081,0.026557,-0.108326,0.053621,-0.053667,-0.005841,-0.11899,0.051788,0.045789,0.017007,-0.014744,0.000276,-0.102408,-0.014863,-0.044824,0.07083,-0.046453,-0.058584,0.052209,0.054361,0.015598,-0.014997,-0.013526,0.050943,-0.026301,-0.001117,0.013691,-0.042763,0.05024,-0.011062,0.041559,-0.06792,-0.038876,0.058981,0.031,-0.013464,0.027483,-0.018659,-0.02451,0.048266,0.083805,0.012314,-0.050906,0,-0.029913,0.040366,0.02148,-0.02961,-0.033853,-0.051341,0.024575,0.02242,0.021678,0.121846,0.019853,-0.011285,-0.016655,0.041579,0.01781,-0.026627,0.041995,0.014277,-0.085003,-0.022203,-0.034882,-0.023459,0.086339,-0.051777,0.010185,-0.003111,0.0238,-0.01829,0.019005,0.02693,-0.007306,0.027106,-0.042237,0.041413,0.026327,-0.133955,-0.049817,-0.030976,-0.021929,0.040456,-0.008463,0.066257,-0.040366,-0.054111,-0.049958,0.005405,0.022113,0.047757,0.015077,0.075313,0.032185,-0.035936,-0.060074,0.005349,-0.011326,0.013268,0.094121,0.064537,-0.000739,0.060655,-0.026217,0.046535,-0.008755,0.082427,0.041712,-0.028408,0.019136,0.104688,0.057607,0.089312,0.038296,0.111578,0.045578,-0.032771,0.02745,-0.006607,0.038349,-0.034805,-0.053088,0.027888,-0.018805,0.008391,-0.052711,0.013043,0.020485,0.071059,0.054046,-0.045798,0.022229,-0.030451,0.017173,-0.040306,-0.098873,0.02085,-0.111726,-0,0.052222,0.091149,-0.032573,-0.053962,0.025119,-0.030071,-0.056321,-0.086294,0.060927,0.046199,-0.017928,-0.01753,0.108176,0.005259,0.01644,-0.09835,-0.006458,-0.037764,-0.076175,-0.026424,-0.064541,-0.041864,-0.029104,0.02778,-0.099183,0.002453,-0.038442,-0.011516,0.003767,-0.019692,-0.046336,-0.054763,-0.023671,-0.082876,-0.053609,-0.003049,0.025586,0.023732,-0.072121,-0.017655,0.041904,0.012125,-0.017536,-0.109853,-0.098946,0.054613,-0.01015,0.017362,-0.074116,-0.000521,-0.055434,0.028307,-0.09361,0.041225,-0.04644,0.069222,-0.01974,-0.012737,0.055147,-0.04891,-0.031996,0.000123,-0.032357,0.022387,0.058167,-0.002642,0.039052,-0.047842,0.079595,0.049157,0.000459,0.025156,-0.024291,0.091364,-0.091813,0.007538,-0.010497,-0.051562,0.057753,0.018064,0.053875,-0.065255,-0.038617,0.025148,0.069931,0.020404,0.093265,0.036983,-0.008713,-0.038212,0.004338,0.089357,-0.004214,-0.002162,-0.025367,-0,-0.165675,0.006333,-0.137068,-0.011802,0.040976,-0.120813,0.043169,0.06295,-0.042522,0.001977,0.000381,0.05081,0.016602,0.029262,-0.060731,-0.034091,0.027958,-0.015151,-0.005831,-0.012306,0.003073,0.057518,0.007211,-0.008,0.057365,-0.048127,-0.09173,0.075493,0.062302,0.010952,-0.005628,0.020324,-0.019813,-0.010865,0.041671,-0.005377,-0.067466,0.020266,0.053487,0.000768,0.064045,0.039331,-0.018896,0.072337,0.019046,0.032219,0.038561,-0.154546,0.003015,-0.112281,0.022826,-0.044261,-0.021783,0.08677,-0.023322,0.007317,-0.011792,-0.046136,0.109399,0.013058,-0.013604,-0.00711,-0.0973,-0.042938]	FGA: Fourier-Guided Attention Network for Crowd\nCount Estimation\nYashwardhan Chaudhuri\nIIIT-Delhi\nyashwardhan20417@iiitd.ac.inAnkit Kumar\nIIT-Bombay\nak670676@gmail.comArun Balaji Buduru\nIIIT-Delhi\narunb@iiitd.ac.inAdel Alshamrani\nUniversity of Jeddah\nasalshamrani@uj.edu.sa\nAbstract —Crowd counting is gaining societal\nrelevance, particularly in domains of Urban Planning,\nCrowd Management, and Public Safety. This paper\nintroduces Fourier-guided attention (FGA), a novel\nattention mechanism for crowd count estimation\ndesigned to address the inefficient full-scale global\npattern capture in existing works on convolution-\nbased attention networks. FGA efficiently captures\nmulti-scale information, including full-scale global\npatterns, by utilizing Fast-Fourier Transformations\n(FFT) along with spatial attention for global features\nand convolutions with channel-wise attention for\nsemi-global and local features. The architecture of\nFGA involves a dual-path approach: (1) a path for\nprocessing full-scale global features through FFT,\nallowing for efficient extraction of information in\nthe frequency domain, and (2) a path for processing\nremaining feature maps for semi-global and local\nfeatures using traditional convolutions and channel-\nwise attention. This dual-path architecture enables\nFGA to seamlessly integrate frequency and spatial\ninformation, enhancing its ability to capture diverse\ncrowd patterns. We apply FGA in the last layers of two\npopular crowd-counting works, CSRNet and CANNet,\nto evaluate the module’s performance on benchmark\ndatasets such as ShanghaiTech-A, ShanghaiTech-B,\nUCF-CC-50, and JHU++ crowd. The experiments\ndemonstrate a notable improvement across all datasets\nbased on Mean-Squared-Error (MSE) and Mean-\nAbsolute-Error (MAE) metrics, showing comparable\nperformance to recent state-of-the-art methods.\nAdditionally, we illustrate the interpretability using\nqualitative analysis, leveraging Grad-CAM heatmaps,\nto show the effectiveness of FGA in capturing crowd\npatterns.\nIndex Terms —Crowd Count Estimation, Fast Fourier\nTransformation, Attention, Channel Attention, Spatial\nAttention, CNN\nI. Introduction\nCrowd count estimation (or crowd counting) involves\nestimating the number of individuals in a particular crowd\nscene. Its utility in public safety, crowd management,\nurban planning, and healthcare makes it relevant in\ncomputer vision. Crowd counting becomes challenging\nin large crowd scenes where problems such as large\nforeground-background imbalances, occlusions, and\nperspective distortion arise frequently. Density-based\ncrowd-counting methods [1] [2] [3] [4] is widely accepted\nas a solution to this problem. It involves predicting\nFig. 1: Left: Image of a crowd scene as input to the\nneural network. Right: Density map of The crowd scene.\nBrighter spots are noticed in the top right corner of the\ndensity map where crowd density is higher and becomes\nless visible towards the left where there Is less crowd\ndensity.\ncrowd density maps (Figure 1), where the sum of pixel\nvalues in a density map gives the number of people in\nit. Crowd counting has progressed significantly since the\nintroduction of deep learning, with works such as MCNN\n[3], CSRNet [4], OURS-CAN [5], ASPDNet [2] being\nwidely accepted as a possible solution.\nMost density map-based solutions employ a CNN [6]-\nbased approach to regress crowd counts. The following\nmethods are promising but remain constrained by the\nconvolutional kernel’s receptive field, leading to inefficient\ncapture of global or long-range patterns in models. A\nglobal receptive field in crowd counting allows the network\nto capture information from a wider context, ensuring\nthat it considers the overall layout of the crowd and\naccounts for variations in crowd density distribution.\nMany attention-based works such as MAN [7], DMCNet\n[8], JANet [9], DA2Net [10] have gained popularity because\nof their ability to understand large-scale dependencies\nthrough attention networks. BBA-net [11], proposes an\nattention-based network designed to capture the fine-\ngrained details in spatial locations. RFSNet [12] introduces\na patch-wise recurrent self-attention network for spatio-\ntemporal crowd counting in video. Although these CNN\nmethods perform exceptionally well, they only utilize\nconvolutions capable of processing information in a\nlocal neighbourhood, ignoring the large-scale pixel-to-pixelarXiv:2407.06110v1  [cs.CV]  8 Jul 2024\n\nFig. 2: FGA Module: The module has two feature extraction sections, as shown in the above figure. Left: The local\nfeature extraction takes a fraction of the input feature maps for local processing. Right: The global feature extraction\ntakes another fraction as input from feature maps for global processing. The spectral block captures full-scale global\nfeatures. ##: Refer to Figure 3 for more details. #: refer to Figure 4 for more details on attention blocks.\ncontext; thus, using convolutional layers alone can prove\ninefficient for understanding full-scale global patterns. To\nsolve this problem, we suggest a novel neural architecture\nnamed the Fourier-Guided Attention (FGA) module,\ndrawing inspiration from the Fast Fourier Convolution\n(FFC) [13] and [1]. This module is designed for long-\nrange context-aware crowd counting, seamlessly combining\nFFC, spatial attention, and channel attention into a\nsingle unit. FFC operates in the spatial and frequency\ndomains, allowing FGA to process information in both\nlocal and global receptive fields. At the same time,\ndifferent attention mechanisms focus on amplifying the\nfine-grained features from different parts of the input\nsequence to capture relevant information. The proposed\nframework can be integrated into existing crowd-counting\nmethods to attend to full-scale global features.\nTo conclude, our contributions are mainly threefold:\n•A novel dual-path architecture utilizing FFC and\nAttention mechanisms incorporating local and global\ncontext into a single pluggable unit for existing works.\n•Two simple FGA integrated architectures with\ncomparable performances to the state-of-the-art\nmethods in crowd counting.\n•A thorough qualitative and quantitative evaluation of\nour proposed approach with four public benchmark\ndatasets: Shanghai-Tech Part A, Shanghai-Tech Part\nB, JHU++ crowd, and UCF-CC-50, along with\nan extensive ablation study to understand the\ncontribution of each part in the FGA module.II. Related Work\nA. Density Based estimation\nMost recent crowd-counting methods employ a variation\nof CNN to predict density maps from crowd images. The\ndensity maps represent the spatial distribution of people\nin the image, with brighter regions depicting higher crowd\ndensity. Numerous approaches have been proposed to\nmitigate the impact of scale variations, such as MCNN [3],\nwhich employs a multi-column architecture with different\nkernel sizes to capture scale variation across a crowd scene\neffectively. CSRNet [4] and CANNET [5] use single-column\nwith a dilated convolution layer. certain encoder-decoder\nmethods like MRCNet [14], [15] incorporate contextual\nand detailed local information by integrating high- and\nlow-level features through several lateral connections. The\npoint-based framework [16] utilizes one-to-one matching\nwith doted annotation, while [17] makes patch-level\nfeature selection. Some methods [18] [19] [20] reduce\nthe Gaussian noise during annotation and density map\ngeneration to give better predictions. In GauNet [21], the\nconvolution filter is replaced by locally connected Gaussian\nkernels. The work proposes a low-rank approximation\naccompanied by translation invariance to implement\nGaussian convolution for density estimation.\nAlthough efficient in capturing local features of crowd\nscenes, the methods are inefficient in capturing large-\nscale pixel-by-pixel information. Attention-based models\nare introduced to address the mentioned issue.\n\nB. Attention based methods\nAttention mechanisms [22] [23] have proven to be highly\nefficient in addressing various computer visio...	all-MiniLM-L6-v2	completed	2025-08-03 20:43:39.769098+00	2025-08-03 20:43:39.769098+00	\N	\N	\N
c2ea925c-2629-4ecb-93e8-fbdef038a701	6300b3d8-1cdc-4a76-a5a9-4eaae00352e7	all-MiniLM-L6-v2	\N	\N	\N	2025-08-03 20:44:01.489371+00	2025-08-03 20:44:01.489371+00	[-0.098898,-0.015266,-0.048416,-0.042266,-0.006372,-0.047235,-0.002838,0.066309,-0.045767,-0.044717,-0.096513,-0.029223,0.001669,-0.012336,0.07513,-0.013849,0.033154,0.05941,-0.028927,0.044379,0.030871,-0.015468,-0.104744,0.007009,0.032916,0.027838,0.015121,-0.067195,0.074555,-0.005069,0.032079,0.04667,0.011806,0.074635,-0.008272,0.034913,-0.045116,-0.04693,-0.049323,-0.075511,-0.080186,-0.018865,0.010031,-0.021934,0.03014,-0.007409,0.023443,0.005888,-0.098849,-0.015706,-0.030198,-0.057358,-0.000439,-0.008324,-0.052713,-0.046284,0.027235,-0.069898,0.070716,-0.044339,-0.082779,-0.02331,-0.03431,0.029074,-0.032177,-0.052087,0.094784,-0.038455,0.031176,0.004625,-0.095443,0.001963,-0.073394,0.108305,-0.083357,-0.012489,0.095169,0.002176,0.059782,-0.06156,0.099297,0.086023,0.007258,0.045823,0.034494,-0.052524,-0.01492,0.054736,0.063618,0.012508,0.054367,0.025309,0.073595,0.00068,0.06439,-0.00359,0.03146,-0.077492,-0.027042,0.080322,-0.041475,0.076578,0.029588,-0.014184,-0.06487,0.003741,0.002899,0.009892,-0.003605,-0.057568,0.025506,0.010862,0.011146,-0.097072,0.008852,0.009875,0.00955,-0.018648,0.025701,-0.026757,-0.067961,-0.000478,-0.022297,0.056934,0.1031,-0.068164,-0.109072,0,0.009161,0.029123,-0.082883,-0.030273,0.018448,-0.044059,0.035972,-0.007986,-0.080557,0.048934,-0.030189,0.020074,0.002521,0.056583,0.101952,0.007128,0.090404,0.003745,-0.050567,-0.054538,0.041308,0.057204,0.058519,-0.033973,0.048101,0.102579,0.094944,-0.129669,0.005263,0.042849,-0.040201,-0.045213,0.001397,0.081144,0.08262,-0.020537,-0.031554,-0.047516,0.102897,0.012422,0.006043,0.026411,-0.001089,-0.086164,0.009306,-0.031561,-0.021597,0.082992,0.01615,-0.031025,0.033839,0.021859,-0.054594,0.024269,0.001729,-0.00757,-0.091425,0.033137,0.035809,0.125172,-0.02157,0.050094,-0.041065,0.008238,-0.053683,-0.064262,-0.069993,0.020441,0.063152,0.050314,-0.03784,-0.010339,0.032106,0.029565,0.011928,-0.007082,0.027607,-0.056641,0.01135,0.00947,-0.069997,0.077057,0.009509,-0.007221,0.018519,-0.108087,-0.025788,0.001029,-0.09943,-0.067079,-0.032566,-0.135098,0.069036,-0.002403,-0.069309,-0,-0.026128,-0.020424,-0.080709,0.074197,-0.047691,-0.08162,0.041523,-0.078698,-0.044829,-0.008171,-0.056604,-0.005859,0.059522,0.020205,0.053314,-0.050619,-0.046812,-0.092937,-0.059587,0.014593,-0.048163,0.042179,-0.001757,-0.042346,-0.008211,0.033794,-0.011173,0.042084,0.005762,0.064472,-0.009207,0.011568,-0.047332,0.005035,0.019573,-0.035038,0.001943,0.03157,0.023686,0.007919,0.144828,-0.049614,0.034483,-0.007647,0.03431,0.02665,-0.105888,0.006088,0.070977,-0.103017,0.03871,-0.019356,0.021113,0.009041,-0.025719,-0.076628,0.029417,-0.016316,-0.059897,-0.036843,-0.006399,-0.00665,0.115413,-0.019842,0.08234,0.085993,-0.061657,-0.059554,-0.012914,-0.03132,0.080368,-0.070043,-0.082233,-0.001679,-0.0693,0.070296,0.028224,-0.055812,0.062602,0.034265,0.002912,0.04642,0.016053,0.016943,-0.043006,0.003139,0.040904,0.016282,0.013074,-0.033585,-0.021993,0.102035,0.061402,0.078522,0.002971,-0,0.005285,-0.017958,-0.061037,0.071192,0.035693,0.019264,0.022637,-0.050441,-0.008649,-0.000924,0.053612,-0.070941,0.001065,-0.044604,0.110525,0.044157,-0.012423,-0.02049,-0.061222,-0.072731,0.004686,0.047613,-0.026652,0.006091,-0.07043,-0.086041,0.006063,0.016931,0.103267,0.031351,-0.010055,0.043391,-0.005841,0.018862,0.066902,0.010149,0.01386,-0.002842,0.059399,0.062827,0.03121,0.0669,5e-06,0.006654,-0.016684,-0.003881,0.001363,-0.089701,-0.016776,0.048367,-0.015806,0.030205,-0.048963,0.059392,0.014251,0.0504,-0.091498,-0.094719,0.021773,0.060315,-0.001745,0.011575,0.028796,0.029544]	arXiv:2410.16690v2  [cs.PL]  23 Oct 2024C-lisp and Flexible Macro Programming with S-expressions\nVedanth Padmaraman, Sasank Chilamkurthy\nAbstract\nLlama.lisp is a compiler framework intended to target oﬄoad processor backends such as GPUs, using\nintermediate representation languages (IRs) that are devi ce-agnostic. The Llama.lisp IRs are formulated\nas S-expressions. This makes them easy to generate using hig her level programming languages, which\nis one of the primary goals for Llama.lisp. The highest IR lay er currently implemented in Llama.lisp is\nC-Lisp. In this paper, we describe the macro system develope d for the Llama.lisp compiler framework.\nWe show how we implemented FFI bindings as an example of this s ystem.\nCompilers are workhorses of performance behind all AI algor ithms. Making algorithms work eﬀectively on\nGPUs is especially hard – called kernel programming. The com piler ecosystem around GPUs is especially\nfragmented. They are supposed to allow for performance port ability between diﬀerent hardware architecture.\nUnfortunately, this is usually not the case.\nWe are designing a compiler framework called llama.lisp [1] to solve this problem. As suggested by the\nname, the framework is highly inspired by Lisp and its syntax , S-expressions. A multi layered approach is\nadopted to tame the complexity of writing such a compiler fra mework. We implement C-lisp as one such\nlayer. We show how lisp syntax has allowed for unique meta pro gramming capabilities while being simple\nboth to understand and implement.\n1. C-Lisp: Structured LLVM IR\nC-Lisp serves as a structured programming [2] interface to t he LLVM [3] instruction set, with semantics\nmodelled after the C language [4]. The S-expression syntax f orms the base of the C-Lisp syntax. An S-\nexpression can be either a token or a list, the elements of whi ch are also S-expressions. The ﬁrst element of\na list usually speciﬁes an action (in which case it is a token) , and the remainder of the elements specify the\narguments to that action. By a slight extension of logic, S-e xpressions can also be viewed as trees: a list\nrepresents an internal node, the ﬁrst element of the list the node type, and the remainder of the elements\nthe node’s children. For example, consider the following va riable declaration in C:\nint var;\nThe root node of the abstract syntax tree (AST) for this state ment is a declaration node; the children of the\nroot node are the type intand the variable reference var. One could represent this AST using S-expressions\nlike so:\n(declare var int)\nAnd it so happens that this is the exact syntax for variable de clarations in C-Lisp.\nMost expression opcodes in C-Lisp (i.e. directives that spe cify some computation) exhibit a close correspon-\ndence to instruction opcodes in the LLVM IR, in that they perf orm the same operations and take the same\nkinds of arguments. For example, the LLVM IR implements the fadd opcode for integer addition, with the\nsyntax\n<result> = fadd [fast-math flags]* <ty> <op1>, <op2>\nC-Lisp exposes a single form of this instruction, consistin g of the compulsory operands, through its fadd\nexpression opcode:\n(fadd <op1> <op2>)\n1\n\nOwing to the adoption of C semantics, it can be noted that the r esult is not speciﬁed in the fadd expression;\nthesetopcode fulﬁlls that purpose, and can be used with the fadd expression as an operand. Additionally,\nthe type is inferred, not explicitly stated.\nAs an illustration of C-Lisp, consider the following C funct ion to add the product of two numbers to the\ncontents of a pointer. The function returns nothing, takes o ne pointer to a 64-bit integer and two 32-bit\nintegers as arguments (the bit widths are platform-speciﬁc , but we shall assume these).\nvoid muladd (long int * res, int a, int b) {\nint mul_res = a * b;\n*res = *res + mul_res;\n}\nAn equivalent C-Lisp implementation would be:\n(define ((muladd void) (res (ptr int64)) (a int) (b int))\n(declare mul_res int)\n(set mul_res (mul a b))\n(store res (add (load res) (sext mul_res int64))))\nOn the face of it, there is a world of diﬀerence between the two versions. However, on closer observation, the\nC-Lisp version closely resembles the AST of the C version. Co nsider the assignment of mul_res in C: it is\nan assignment expression with mul_res as its ﬁrst operand and a * b as its second. Further recursing into\nthe second operand, it is a multiplication expression with aandbas operands. The C-Lisp version reﬂects\nthis structure accurately, with setdenoting an assignment and muldenoting a multiplication.\nAs a result, both implementations have similar semantics, a nd the executables produced from both per-\nform equally well. However, the adoption of S-expressions m akes it much more conducive to generate and\nprogrammatically interact with the C-Lisp version.\nOne main point of diﬀerence between semantics of two version s is the use of implicit casting. The C version\nadds mul_res , a 32-bit integer, to the contents of res, a 64-bit integer. This works because a compliant C\ncompiler will insert an implicit cast from a 32- to a 64-bit in teger, and thus behave as if the source program\nhad stated\n*res = *res + (long int) mul_res;\nC-Lisp, on the other hand, employs no implicit action whatso ever. The programmer is forced to explicitly\ncastmul_res to a 64-bit integer. This helps keep the C-Lisp language’s im plementation concise and simple.\nAdditionally, the absence of implicit actions simpliﬁes th e analysis of these programs.\nTo ease the process of C-Lisp code generation, the JavaScrip t Object Notation (JSON) is used as an exchange\nformat for C-Lisp. JSON has support for lists as well as the ba sic token types (integers, ﬂoating-point\nnumbers and so on), which makes it an ideal choice for seriali zing S-expressions. Additionally, JSON enjoys\nsupport in most mature programming languages. The transfor mer from S-expression to JSON is written in\nGuile Scheme, and as such uses most of Scheme’s conventions f or capturing constructs such as unquote .\n2. A Macro Preprocessor\nC-Lisp is intended to be minimal; most computation can be exp ressed in C-Lisp with reasonably simple\ncode, and there is seldom more than one way to do so. This neces sitates a strong macro system: one that\nenables extensions of C-Lisp, reducing the need for feature additions to the language. Prelisp aims to fulﬁll\nthis need, borrowing from the multistage programming [5] pa radigm.\nPrelisp uses Python as the macro language, although any mode rn general-purpose language could have been\nused. On the face of it, using a third-party language for the p reprocessor can make for rather complicated\nmacro deﬁnitions; however, owing to the adoption of the S-ex pression syntactical form, the process of C-\nLisp code generation is greatly simpliﬁed. Thus, Python’s o wnlist data structure make it feasible to\nprogrammatically emit C-Lisp code. Additionally, Python m akes for a good choice because it involves a\n2\n\nminimal learning curve, and it leaves a powerful standard li brary and programming environment at the\nmacro programmer’s disposal.\nThe Prelisp preprocessor takes the input program as a JSON ob ject. Portions of this object are recognized as\nmacro expressions, evaluated using macro deﬁnitions from a supplied Python module (the “macro module”\nhenceforth), and replaced to produce the result. A macro is e xpected to be deﬁned in the global scope of\nthe macro module, and is either referenced directly, like a v ariable, or called, like a function. In both cases,\nthe macro evaluates to a Python object which is substituted i n place of the macro expression and eventually\nserialized back into JSON along with the rest of the program. Macro expressions in the source program are\ndenoted using either the unquote or the unquote-splicing constructs [6], borrowed from the Lisp family.\n2.1. Variable substitution\nunquote can be used to substitute a single expression. The following expression\n; In the source program\n(eq (call getchar) ,EOF)\nis equivalent to the ...	all-MiniLM-L6-v2	completed	2025-08-03 20:44:01.489371+00	2025-08-03 20:44:01.489371+00	\N	\N	\N
90b50d9a-c53d-4a7c-8007-58e497c9decc	c32bdae7-2c1e-4987-9d3d-da9244c3ce68	all-MiniLM-L6-v2	\N	\N	\N	2025-08-03 20:44:57.255099+00	2025-08-03 20:44:57.255099+00	[0.035662,-0.050916,-0.008832,0.045754,0.051573,-0.006542,-0.058223,0.046855,0.013212,-0.046706,-0.002703,0.016556,0.025252,0.054375,-0.07425,-0.014952,0.000953,-0.084703,-0.027418,-0.052441,-0.018585,0.06558,0.102902,0.033082,-0.048545,-0.009535,0.01865,0.005318,-0.017659,0.045374,0.076799,-0.009203,0.037117,0.016342,-0.048703,0.003098,0.053317,0.022995,0.00815,-0.019506,0.057046,-0.057927,0.045681,-0.037515,0.12613,0.018016,-0.137485,0.017543,-0.033228,0.067642,-0.130778,-0.084452,0.020113,0.018778,0.040195,-0.082623,-0.07772,-0.108008,-0.045948,-0.071167,-0.009782,0.005904,-0.025214,0.035182,-0.035068,-0.044493,0.098581,0.019409,0.041759,0.006238,-0.066305,0.032679,-0.034868,0.024891,-0.067535,0.067269,0.030826,-0.039549,0.007959,0.005976,0.031145,0.064895,0.172705,-0.005468,-0.0405,-0.023076,-0.009921,0.049119,-0.044496,-0.001206,0.027707,-0.032519,0.011,-0.021732,0.026277,-0.037137,-0.004253,-0.043252,-0.058461,0.017589,-0.121075,0.026797,-0.013721,0.016845,0.012779,0.00587,0.071866,0.005699,0.036316,-0.054694,0.046928,0.120329,0.021399,-0.070832,0.025004,0.057324,-0.016189,-0.04156,-0.016314,0.079197,-0.078829,-0.102489,-0.022686,-0.006405,0.019947,-0.027819,-0.009398,0,0.042406,-0.001707,0.13019,0.071265,0.050261,-0.030236,-0.047925,-0.011618,0.073147,-0.011101,-0.02521,-0.040364,0.02136,0.11113,-0.093322,0.018347,-0.039584,-0.011318,-0.058207,0.021829,0.016669,-0.034459,0.04536,-0.036512,-0.011395,0.060211,-0.05705,0.093854,0.050017,-0.002987,-0.069669,-0.011938,0.025377,0.0082,-0.090034,-0.007796,-0.061653,-0.039461,0.031292,0.004069,0.034722,-0.00918,-0.028535,0.002498,0.042305,-0.082277,-0.055785,-0.025295,-0.026266,0.069572,0.007672,0.036174,-0.024536,-0.109572,-0.02533,0.01769,0.034505,0.04804,0.038272,-0.002474,0.01946,0.027217,-0.03942,0.020077,-0.05538,0.049083,-0.010204,-0.06964,0.002712,0.078917,-0.025475,0.006195,-0.028244,0.005444,0.083431,-0.091481,0.005621,-0.021952,0.00924,-0.081597,-0.01251,-0.005571,0.118495,0.05493,-0.057357,0.00129,-0.035463,0.005517,-0.0601,-0.03557,0.004811,0.092678,0.004097,0.091243,0.029343,-0,-0.013809,0.02692,-0.06522,-0.056945,0.005866,0.107028,9.8e-05,0.009831,0.040132,-0.107138,0.069207,0.028333,0.014589,-0.010984,-9.2e-05,0.093117,-0.000582,-0.004111,-0.031395,0.039074,-0.05264,0.035103,-0.002754,-0.016596,-0.022762,0.082143,0.095523,-0.015034,-0.026966,0.019887,0.002111,0.005686,-0.093629,0.000626,-0.000204,0.006804,-0.048043,-0.041851,-0.117356,0.007503,-0.005549,0.034144,-0.055297,-0.028251,0.010468,0.075456,0.068327,-0.072571,0.087154,-5.3e-05,0.018219,0.028223,-0.044268,-0.014099,-0.022399,0.001155,0.01268,-0.139783,-0.03154,-0.044699,-0.148388,-0.003253,-0.02504,-0.047972,0.082275,-0.014349,-0.004721,0.006127,0.088954,-0.034572,-0.047525,-0.0165,-0.128299,-0.086976,-0.003994,0.04518,-0.109306,-0.010387,-0.0464,-0.001382,-0.013452,-0.078054,0.043733,-0.02112,0.018764,0.026234,-0.051176,-0.074005,-0.017169,0.030764,-0.007991,0.040685,-0.086405,-0.016419,-0.06547,-0,0.010574,-0.063053,0.003,0.018988,-0.013834,0.060297,-0.105273,0.067957,-0.035127,0.050193,0.045462,0.087575,0.010677,0.015689,-0.049994,0.02278,-0.120709,-0.016986,-0.055411,-0.023212,-0.002286,-0.03212,0.024102,-0.025782,0.058629,0.010456,-0.019976,0.076748,-0.035571,-0.020844,-0.028444,0.002065,-0.012347,0.081582,0.020548,0.022943,0.108935,-0.003768,-0.0298,0.012104,0.058459,0.018557,-0.050218,0.008883,-0.006416,-0.001119,0.003385,-0.019782,0.011219,-0.036685,0.013484,0.024206,0.030394,0.147307,0.042928,-0.009843,-0.030526,-0.036293,0.052397,-0.003489,0.07452,-0.038351,-0.017377,0.063164]	https://www.isohe.org/medical -advances -and-innovations -journal                                 \n                                               August   2023 | Volume 1 | Issue 3 1 \n   https://www.isohe.org/medical -advances -and-innovations -journal      August   2023 | Volume 1 | Issue 3 \n                                 \n \n Machine Learning -driven Analysis of Gastrointestinal Symptoms in Post -COVID -\n19 Patients  \nMaitham G. Yousif*1 ,Fadhil G. Al -Amran2, Salman Rawaf3,  Mohammad Abdulla \nGrm t4  \n1Biology Department, College of Science, University of Al -Qadisiyah, Iraq, Visit ing Professor in Liverpool John Moors \nUniversity, Liverpool, United Kingdom  \n2Cardiovascular Department, College of Medicine, Kufa University, Iraq  \n3Professor of Public Health Director, WHO Collaboration Center , Imperial College, London, United Kingdom  \n4Al-Sadder Teaching  Hospital , Al-Najaf Health office , Najaf , Iraq  \nReceived 3/10/2022 , Accepted 8/2/2023, Published 6/8/2023.  \n This work is licensed under a  Creative Commons Attribution 4.0 International License . \n \n \nAbstract  \n   The COVID -19 pandemic, caused by the novel coronavirus SARS -CoV-2, has posed significant health \nchallenges worldwide. While respiratory symptoms have been the primary focus, emerging evidence \nhas highlighted the impact of COVID -19 on various organ systems, including the gastrointestinal (GI) \ntract. This study, based on data from 91 3 post -COVID -19 patients in Iraq collected during 2022 and \n2023, investigates the prevalence and patterns of GI symptoms in individuals recovering from COVID -\n19 and leverages machine learning algorithms to identify predictive factors for these symptoms.  The \nresearch findings reveal that a notable percentage of post -COVID -19 patients experience GI \nsymptoms during their recovery phase. Diarrhea emerged as the most frequently reported symptom, \nfollowed by abdominal pain and nausea. Machine learning analysis un covered significant predictive \nfactors for GI symptoms, including age, gender, disease severity, comorbidities, and the duration of \nCOVID -19 illness. These findings underscore the importance of monitoring and addressing GI \nsymptoms in post -COVID -19 care, w ith machine learning offering valuable tools for early \nidentification and personalized intervention.  This study contributes to the understanding of the long -\nterm consequences of COVID -19 on GI health and emphasizes the potential benefits of utilizing \nmachi ne learning -driven analysis in predicting and managing these symptoms. Further research is \nwarranted to delve into the mechanisms underlying GI symptoms in COVID -19 survivors and to \ndevelop targeted interventions for symptom management.  \nKeywords : COVID -19, gastrointestinal symptoms, machine learning, predictive factors, post -COVID -19 \ncare, long COVID.  \n*Corresponding author:  Maithm Ghaly Yousif  matham.yousif@qu.edu.iq     m.g.alamran@ljmu.ac.uk\n\nhttps://www.isohe.org/medical -advances -and-innovations -journal                                 \n                                               August   2023 | Volume 1 | Issue 3 2 \n   https://www.isohe.org/medical -advances -and-innovations -journal      August   2023 | Volume 1 | Issue 3 \n                                 \n \n       \nIntroduction  \n   The COVID -19 pandemic, caused by the novel \ncoronavirus SARS -CoV-2, has brought about a \nmultitude of health challenges and continues to \nbe a subj ect of extensive research worldwide. \nBeyond its immediate respiratory \nmanifestations, COVID -19 has been associated \nwith a wide array of health issues that extend \ninto the post -acute phase, affecting various \norgan systems [ 1-3]. Among these, the \ncardiovascula r system has garnered significant \nattention due to its susceptibility to infection \nand the potential for severe complications, \nincluding myocardial ischemia and \natherosclerosis [ 4-6]. Additionally, various \nmedical conditions, such as cancer [ 7-9], \npreeclampsia  [10-13], and infectious diseases \nlike urinary tract infections [ 14-17], continue to \nbe prevalent, further complicating the \nhealthcare landscape.  This introduction serves \nas a gateway to the exploration of the intricate \nrelationship between COVID -19 and various \nhealth conditions, with a specific focus on the \ncardiovascular system, cancer, and infectious \ndiseases. It also sets the stage for understanding \nthe broader context of our research endeavors.  \nThe objective of this study is to investigate the \neffects of COVID -19 on cardiovascular health, \ncancer incidence, and the prevalence of \ninfectious diseases in the context of the Iraqi \npopulation. To achieve this, we have leveraged a range of data sources, including clinical trials \n[18-22], longitudinal studies [ 23-25], and \nmolec ular investigations [ 26-29]. Our research \nencompasses a diverse array of medical \nconditions and seeks to shed light on the \nmultifaceted consequences of COVID -19. As we \nembark on this exploration, we will draw upon a \nrich body of literature that delves into the  \npathophysiology and clinical outcomes of these \nhealth conditions [ 30-33]. In this context, we \naim to provide a comprehensive overview of the \nimpact of COVID -19 on cardiovascular health, \ncancer incidence, and infectious diseases. Our \ninvestigation spans severa l years, primarily \nfocusing on data collected during 2021, 2022, \nand 2023, to offer a current and evolving \nunderstanding of these interrelated health \ndomains. This research is underpinned by an \narray of scientific studies and clinical trials \nconducted with in Iraq [ 34-36], ensuring the \nrelevance and applicability of our findings to the \nlocal healthcare landscape.  In the following \nsections, we will delve into the details of our \nresearch methodology, data sources, analytical \ntechniques, and key findings. Through this \ncomprehensive examination, we endeavor to \ncontribute to the growing body of knowledge \nsurrounding COVID -19's far -reaching impact on \nhuman health.  \n \nMaterials  and Methods  \nStudy Design:  \nData Collection:  We gathered medical data from \na total of 913 patients who sought treatment at \nvarious hospitals in Iraq during the years 2022 \nand 2023. These patients had previously been diagnosed with COVID -19. \nData Sources:  The data sources for this study \nincluded electronic health records, clinical trials, \nand longitudinal studies. We accessed de -\nidentified patient records with the necessary \nethical and legal approvals.\n\nhttps://www.isohe.org/medical -advances -and-innovations -journal                                 \n                                               August   2023 | Volume 1 | Issue 3 3 \n   https://www.isohe.org/medical -advances -and-innovations -journal      August   2023 | Volume 1 | Issue 3 \n                                 \n \n Study Duration:  Data collection and analysis \ntook place over a span of 12 months, starting in \nJanuary 2022 and concluding in December \n2023.  \nData Preprocessing:  \nData Cleaning:  We conducted rigorous data \ncleaning procedures to ensure data accuracy \nand consistency. This inv olved identifying and \nrectifying missing values, outliers, and \ninconsistencies in the dataset.  \nData Integration:  We integrated data from \ndiverse sources, including clinical trials, patient \nrecords, and laboratory reports, into a unified \ndataset for compreh ensive analysis.  \nFeature Selection:  \nFeature Engineering:  To identify relevant \nfeatures for analysis, we employed feature \nengineering techniques, considering various \npatient demographics, comorbidities, and \nCOVID -19-related variables.  \nStatistical Analysis:  \nDescriptive Statistics:  Descriptive statistics were \nempl oyed to provide an overview of the patient \ncohort, including mean age, gender distribution, \nand geographical locations within Iraq.  \nInferential Statistics:  Inferential statistical \nmethods, such as t -tests and chi -square tests, \nwere utilized to compare the prevalence of \nspec...	all-MiniLM-L6-v2	completed	2025-08-03 20:44:57.255099+00	2025-08-03 20:44:57.255099+00	\N	\N	\N
7241df3b-c8ba-46b6-8f08-fe25b908ff2a	f9c43b41-6e01-4571-ae88-909821c25fed	all-MiniLM-L6-v2	\N	\N	\N	2025-08-03 22:03:37.537298+00	2025-08-03 22:03:37.537298+00	[-0.03966,-0.110786,0.075428,0.019729,0.026371,0.014394,-0.02862,-0.082014,0.021396,-0.099009,-0.007594,-0.049654,0.020682,0.067832,-0.090051,-0.056068,0.147262,-0.005729,-0.129307,-0.009985,-0.012078,-0.017247,-0.007727,-0.022335,0.05157,-0.016252,0.017554,-0.057798,0.039265,-0.078791,0.015627,0.058527,0.02457,0.083914,-0.026666,0.114061,0.00539,-0.024353,-0.023839,-0.00013,0.04105,0.004879,0.010447,0.053754,0.063244,0.013254,0.081551,-0.087885,0.087597,0.035031,-0.018719,0.083182,-0.031621,0.148158,-0.046399,-0.001309,0.016453,0.039138,-0.005653,0.07003,0.019399,-0.047591,0.043882,-0.044938,-0.032807,-0.047287,-0.016025,0.017706,0.005614,-0.086619,0.03891,0.111769,-0.026015,0.011528,-0.005147,0.012642,0.048878,-0.04641,0.048631,-0.086283,0.043853,-0.039254,0.077916,0.027479,0.077754,-0.006899,-0.096597,0.06199,-0.104727,-0.059499,-0.00934,0.020494,-0.010239,-0.026498,0.011074,0.032579,0.013901,-0.054576,-0.063261,0.106021,-0.043095,0.016465,0.049234,-0.01184,-0.020314,-0.005089,0.045857,0.036052,0.027673,-0.05021,0.080677,-0.006511,0.041934,0.016458,0.040718,0.007188,-0.004353,0.024671,0.111182,-0.052078,-0.091295,-0.021042,-0.093781,0.014835,0.022196,-0.021319,-0.011444,0,-0.00467,0.06907,-0.020988,0.037232,0.003087,-0.032275,-0.014532,0.076518,-0.04669,0.035808,-0.029459,-0.013608,-0.09827,0.044631,0.01451,-0.001526,-0.010663,-0.055697,-0.023078,-0.068536,-0.022756,-0.055871,-0.021165,0.004898,-0.013987,-0.016711,0.039854,-0.005631,-0.007996,0.004111,-0.00052,0.065633,0.048159,0.07332,0.033666,-0.024978,-0.106065,0.034832,0.047389,-0.042554,0.001172,0.046231,-0.120014,-0.069327,-0.109362,-0.054721,0.043887,-0.009618,-0.010712,0.052028,0.109587,-0.009073,-0.042432,-0.03118,-0.026001,-0.046521,0.06461,0.018547,0.028933,0.085929,0.035759,0.004122,-0.069625,0.132397,0.007934,-0.031826,0.02569,0.1231,-0.013088,0.001772,-0.049859,0.036717,0.039711,-0.019988,0.032694,-0.01286,-0.037662,-0.08061,0.015991,0.064271,-0.009611,0.012129,0.019304,-0.013773,-0.043756,0.083553,0.039517,-0.057937,0.056696,0.006206,-0.034478,-0.054017,-0.017816,0.013832,-0.030516,-0,0.000942,0.084014,-0.067794,0.028695,-0.047036,-0.003647,0.05358,0.004579,0.021101,0.010938,0.050689,0.044109,0.026102,-0.043161,0.01528,-0.019087,-0.016443,-0.053073,-0.048028,0.03933,-0.017254,0.034449,-0.09725,0.061177,-0.099709,0.043159,-0.053954,0.014793,-0.035753,0.025509,-0.042965,-0.030761,0.013818,-0.02914,-0.052692,-0.009511,0.021472,0.013948,-0.021848,0.00308,0.046073,-0.04242,-0.062816,0.014298,-0.041541,-0.02445,-0.027412,0.055852,0.000423,0.081353,-0.031419,0.063614,-0.082266,0.063083,0.021659,-0.019234,-0.032851,0.062305,0.0697,-0.015753,-0.066412,-0.069112,-0.051227,-0.022358,0.012307,-0.014351,-0.075738,0.023156,0.03025,0.101619,0.025158,-0.011721,0.013807,0.001444,-0.078809,-0.058938,-0.030891,0.032218,0.038843,0.036993,0.028735,-0.037974,0.024159,0.046022,0.126252,0.050489,0.016574,-0.036865,0.022069,0.000666,-0.053942,0.016232,-0.040748,-0.019463,0.007078,-0,-0.079473,0.043059,-0.045179,-0.091177,-0.038648,-0.136057,0.020649,0.183058,0.00767,-0.015138,0.017682,-0.052235,-0.047414,-0.011453,-0.015301,0.049486,0.033429,-0.005624,0.041407,0.048616,0.085,-0.000461,0.098287,-0.025947,0.015387,-0.033501,-0.069583,0.087424,0.020139,-0.079448,-0.008106,-0.015113,0.004334,-0.059877,0.055772,0.070579,0.031217,-0.012308,0.012661,0.011315,0.03406,0.043382,-0.013667,0.015361,0.005495,0.02326,0.09582,-0.096835,0.017502,0.00997,0.005947,-0.055578,0.019052,0.021646,-0.007299,-0.0013,0.023769,-0.004831,0.00011,0.119795,-0.042193,0.060408,-0.061084,-0.083589]	CSRNet: Dilated Convolutional Neural Networks for Understanding the Highly\nCongested Scenes\nYuhong Li1;2, Xiaofan Zhang1, Deming Chen1\n1University of Illinois at Urbana-Champaign\n2Beijing University of Posts and Telecommunications\nfleeyh,xiaofan3,dchen g@illinois.edu\nAbstract\nWe propose a network for Congested Scene Recognition\ncalled CSRNet to provide a data-driven and deep learning\nmethod that can understand highly congested scenes and\nperform accurate count estimation as well as present high-\nquality density maps. The proposed CSRNet is composed\nof two major components: a convolutional neural network\n(CNN) as the front-end for 2D feature extraction and a di-\nlated CNN for the back-end, which uses dilated kernels to\ndeliver larger reception ﬁelds and to replace pooling opera-\ntions. CSRNet is an easy-trained model because of its pure\nconvolutional structure. We demonstrate CSRNet on four\ndatasets (ShanghaiTech dataset, the UCF CC50 dataset,\nthe WorldEXPO’10 dataset, and the UCSD dataset) and\nwe deliver the state-of-the-art performance. In the Shang-\nhaiTech Part B dataset, CSRNet achieves 47.3% lower\nMean Absolute Error (MAE) than the previous state-of-the-\nart method. We extend the targeted applications for count-\ning other objects, such as the vehicle in TRANCOS dataset.\nResults show that CSRNet signiﬁcantly improves the output\nquality with 15.4% lower MAE than the previous state-of-\nthe-art approach.\n1. Introduction\nGrowing number of network models have been devel-\noped [1, 2, 3, 4, 5] to deliver promising solutions for crowd\nﬂows monitoring, assembly controlling, and other security\nservices. Current methods for congested scenes analysis are\ndeveloped from simple crowd counting (which outputs the\nnumber of people in the targeted image) to density map pre-\nsenting (which displays characteristics of crowd distribu-\ntion) [6]. This development follows the demand of real-\nlife applications since the same number of people could\nhave completely different crowd distributions (as shown in\nFig. 1), so that just counting the number of crowds is not\nenough. The distribution map helps us for getting more ac-\ncurate and comprehensive information, which could be crit-\nical for making correct decisions in high-risk environments,\nsuch as stampede and riot. However, it is challenging to\ngenerate accurate distribution patterns. One major difﬁculty\nFigure 1. Pictures in ﬁrst row show three images all containing 95\npeople in ShanghaiTech Part B dataset [18], while having totally\ndifferent spatial distributions. Pictures in second row show their\ndensity maps.\ncomes from the prediction manner: since the generated den-\nsity values follow the pixel-by-pixel prediction, output den-\nsity maps must include spatial coherence so that they can\npresent the smooth transition between nearest pixels. Also,\nthe diversiﬁed scenes, e.g., irregular crowd clusters and dif-\nferent camera perspectives, would make the task difﬁcult,\nespecially for using traditional methods without deep neu-\nral networks (DNNs). The recent development of congested\nscene analysis relays on DNN-based methods because of\nthe high accuracy they have achieved in semantic segmen-\ntation tasks [7, 8, 9, 10, 11] and the signiﬁcant progress they\nhave made in visual saliency [12]. The additional bonus of\nusing DNNs comes from the enthusiastic hardware com-\nmunity where DNNs are rapidly investigated and imple-\nmented on GPUs [13], FPGAs [14, 15, 16], and ASICs [17].\nAmong them, the low-power, small-size schemes are es-\npecially suitable for deploying congested scene analysis in\nsurveillance devices.\nPrevious works for congested scene analysis are mostly\nbased on multi-scale architectures [4, 5, 18, 19, 20]. They\nhave achieved high performance in this ﬁeld but the de-\nsigns they used also introduce two signiﬁcant disadvantages\nwhen networks go deeper: large amount of training time\nand non-effective branch structure (e.g., multi-column CNN\n(MCNN) in [18]). We design an experiment to demon-\nstrate that the MCNN does not perform better compared to aarXiv:1802.10062v4  [cs.CV]  11 Apr 2018\n\ndeeper, regular network in Table 1. The main reason of us-\ning MCNN in [18] is the ﬂexible receptive ﬁelds provided\nby convolutional ﬁlters with different sizes across the col-\numn. Intuitively, each column of MCNN is dedicated to a\ncertain level of congested scene. However, the effectiveness\nof using MCNN may not be prominent. We present Fig. 2\nto illustrate the features learned by three separated columns\n(representing large, medium, and small receptive ﬁelds) in\nMCNN and evaluate them with ShanghaiTech Part A [18]\ndataset. The three curves in this ﬁgure share very similar\npatterns (estimated error rate) for 50 test cases with different\ncongest densities meaning that each column in such branch\nstructure learn nearly identical features. It performs against\nthe original intention of the MCNN design for learning dif-\nferent features for each column.\nIn this paper, we design a deeper network called CSR-\nNet for counting crowd and generating high-quality den-\nsity maps. Unlike the latest works such as [4, 5] which\nuse the deep CNN for ancillary, we focus on designing a\nCNN-based density map generator. Our model uses pure\nconvolutional layers as the backbone to support input im-\nages with ﬂexible resolutions. To limit the network com-\nplexity, we use the small size of convolution ﬁlters (like\n33) in all layers. We deploy the ﬁrst 10 layers from\nVGG-16 [21] as the front-end and dilated convolution lay-\ners as the back-end to enlarge receptive ﬁelds and extract\ndeeper features without losing resolutions (since pooling\nlayers are not used). By taking advantage of such innovative\nstructure, we outperform the state-of-the-art crowd count-\ning solutions (a MCNN based solution called CP-CNN [5])\nwith 7%, 47.3%, 10.0%, and 2.9% lower Mean Abso-\nlute Error (MAE) in ShanghaiTech [18] Part A, Part B,\nUCF CC50 [22], and WorldExpo’10 [3] datasets respec-\ntively. Also, we achieve high performance on the UCSD\ndataset [23] with 1.16 MAE. After extending this work to\nvehicle counting on TRANCOS dataset [20], we achieve\n15.4% lower MAE than the current best approach, called\nFCN-HA [24].\nThe rest of the paper is structured as follows. Sec. 2\npresents the previous works for crowd counting and den-\nsity map generation. Sec. 3 introduces the architecture and\nconﬁguration of our model while Sec. 4 presents the exper-\nimental results on several datasets. In Sec. 5, we conclude\nthe paper.\n2. Related work\nFollowing the idea proposed by Loy et al. [25], the po-\ntential solutions for crowd scenes analysis can be classiﬁed\ninto three categories: detection-based methods, regression-\nbased methods, and density estimation-based methods. By\ncombining the deep learning, the CNN-based solutions\nshow even stronger ability in this task and outperform the\ntraditional methods.\nFigure 2. The estimated error of 50 samples from the testing set\nin ShanghaiTech Part A [18] generated by the three pre-trained\ncolumns of MCNN. Small, Medium, Large respectively stand for\nthe columns with small, medium or large kernels in the MCNN.\nMethod Parameters MAE MSE\nCol. 1 of MCNN 57.75k 141.2 206.8\nCol. 2 of MCNN 45.99k 160.5 239.0\nCol. 3 of MCNN 25.14k 153.7 230.2\nMCNN Total 127.68k 110.2 185.9\nA deeper CNN 83.84k 93.0 142.2\nTable 1. To demonstrate that MCNN [18] may not be the best\nchoice, we design a deeper, single-column network with fewer\nparameters compared to MCNN. The architecture of the pro-\nposed small network is: CR(32;3)MCR(64;3)M\nCR(64;3)MCR(32;3)CR(32;3)CR(1;1).CR(m;n )\nrepresents the convolutional layer with m ﬁlters whose size is nn\nfollowed by the ReLu layer. Mis the max-pooling layer. Results\nshow that the single-column version achieves higher performance\non ShanghaiTech Part A dataset [18] with the lowest MAE and\nMean Squared Error (MSE)\n2.1. Detection-based approaches\nMost of the early researches focus on detection-based\napproaches using a moving-window-like detec...	all-MiniLM-L6-v2	completed	2025-08-03 22:03:37.537298+00	2025-08-03 22:03:37.537298+00	\N	\N	\N
9d2a14b0-a613-4b6f-89a7-668922f9488b	3d228d2f-6e0b-438f-828a-432e7e8b7247	all-MiniLM-L6-v2	\N	\N	\N	2025-08-03 22:04:01.534824+00	2025-08-03 22:04:01.534824+00	[-0.054111,-0.00286,0.035128,-0.008168,-0.030656,-0.031506,0.063469,0.083998,-0.040159,-0.002419,0.017181,-0.050732,0.021741,0.035198,-0.057951,-0.1188,0.004119,-0.010869,-0.039148,-0.013609,0.059111,0.080658,0.000946,-0.010587,0.043885,-0.10044,0.026271,-0.062654,-0.047049,0.013375,-0.013253,0.046006,0.004847,0.083493,-0.079188,0.032537,-0.073503,-0.005998,-0.143653,-0.04075,-0.020274,-0.002587,-0.013621,0.039738,0.175915,-0.002807,-0.058501,0.033474,0.002363,-0.008536,-0.079747,-0.030782,0.020643,0.01147,-0.006324,0.000819,-0.04092,-0.010797,0.03274,0.058527,0.065043,-0.006521,0.025866,-0.023517,-0.02966,0.000541,0.045186,-0.04467,0.040747,-0.022105,-0.055652,0.04543,0.010027,0.006205,-0.062462,-0.023082,-0.018308,-0.010695,0.006576,0.015338,0.054069,0.042909,0.086872,0.041273,0.140876,-0.011364,0.019837,0.018334,-0.052113,-0.111547,0.029347,0.028649,-0.137127,0.028813,-0.08641,-0.038794,0.025266,-0.09018,-0.007514,0.065217,-0.053367,-0.044791,0.022266,0.004166,-0.072146,0.010597,0.047745,0.004514,0.078427,-0.027849,0.044585,0.080271,0.00479,-0.056974,-0.081949,0.018013,-0.027626,-0.056396,0.124722,0.058017,-0.085665,-0.01455,0.015039,-0.05816,0.108692,0.079574,0.008266,0,0.032921,0.039045,0.01105,-0.02493,0.01223,-0.001242,-0.007633,0.06696,0.018707,-0.062101,-0.011776,0.031265,-0.03092,-0.000603,0.028516,-0.022895,0.064377,-0.015323,0.017364,-0.012842,-0.085375,-0.071949,0.056584,-0.041367,-0.013525,0.06132,0.082582,0.046122,0.090162,0.018406,0.038214,0.024725,0.083783,-0.070092,0.036651,-0.030266,0.036576,0.047178,0.036022,-0.035933,-0.029441,0.058499,0.00294,-0.089796,0.03907,0.046474,0.018343,0.036415,-0.040316,0.003007,-0.023954,-0.036304,-0.022123,-0.081379,-0.000318,0.068102,-0.071659,0.011351,0.084769,0.012062,-0.008941,0.012246,-0.062196,0.035186,-0.068351,-0.067185,0.039782,0.000588,-0.090157,-0.029218,0.015815,0.003189,0.028676,-0.024332,0.019208,0.079444,0.02403,0.001215,-0.044996,-0.030544,0.050793,0.106964,0.077393,-0.051415,0.026403,-0.024804,-0.031925,-0.006822,-0.067095,-0.017493,-0.045461,0.095384,-0.031695,-0.019184,0.02109,-0,-0.030043,0.010577,-0.015739,-0.007443,0.043595,-0.064078,0.014801,-0.023909,0.037579,-0.067086,0.008458,-0.02109,0.038236,-0.019605,-0.052378,0.063034,-0.142189,0.003781,-0.053735,0.025887,-0.054589,0.05993,-0.018282,0.005104,-0.008469,0.05187,-0.011108,0.092745,-0.076377,-0.063472,-0.001095,-0.078037,-0.062527,0.057011,-0.025791,0.004018,-0.025723,-0.086019,-0.034661,0.071275,0.095374,0.01001,-0.05484,-0.141343,0.073002,-0.03171,0.002526,0.01378,0.047739,0.013013,0.023689,0.03567,-0.096884,-0.019268,-0.07677,0.03287,-0.019043,-0.007323,-0.044598,0.030317,0.014148,-0.12885,-0.007935,0.026363,-0.034859,0.044314,0.094598,0.049368,0.086525,0.059651,-0.030876,-0.019743,-0.073933,-0.01919,-0.008261,0.020438,-0.088772,0.00418,-0.056218,-0.043526,0.102452,-0.098258,0.03026,0.067067,0.044585,0.022631,0.034943,-0.044977,0.032851,-0.032288,-0.125752,0.037363,-0.065324,-0.014354,-0.001052,-0,0.062621,0.004819,0.028315,-0.02421,-0.027612,-0.080044,0.002743,0.069733,0.05693,-0.042146,-0.032579,-0.005386,-0.094124,0.01219,-0.002347,0.023246,0.04017,0.100289,-0.003571,0.024842,0.040834,0.014255,0.035368,-0.001197,-0.010745,-0.080256,-0.05188,0.023046,0.007976,-0.053801,0.01688,0.00833,0.117374,0.054788,0.005319,-0.005225,-0.019854,-0.00993,0.008013,0.053424,-0.026173,0.024484,0.022469,0.016999,-0.055641,-0.07584,0.123005,-0.083475,0.029258,0.006643,-0.03745,-0.011797,0.007156,-0.006561,-0.021558,-0.030295,0.056338,-0.028563,-0.074211,0.039777,-0.001901,-0.027323,-0.038729,0.010643]	Published as ICCCIS 2019 conference paper at IEEE Xplore\nAUTOMATED SMARTPHONE BASED SYSTEM FOR\nDIAGNOSIS OF DIABETIC RETINOPATHY\nMisgina Tsighe Hagos, Shri Kant, Surayya Ado Bala\nResearch and Technology Development Center\nSharda University\nGreater Noida, India\nftsighemisgina,shrikant.ojha,surayyaadob g@gmail.com\nABSTRACT\nEarly diagnosis of diabetic retinopathy for treatment of the disease has been fail-\ning to reach diabetic people living in rural areas. Shortage of trained ophthalmol-\nogists, limited availability of healthcare centers, and expensiveness of diagnostic\nequipment are among the reasons. Although many deep learning-based automatic\ndiagnosis of diabetic retinopathy techniques have been implemented in the litera-\nture, these methods still fail to provide a point-of-care diagnosis. This raises the\nneed for an independent diagnostic of diabetic retinopathy that can be used by\na non-expert. Recently the usage of smartphones has been increasing across the\nworld. Automated diagnoses of diabetic retinopathy can be deployed on smart-\nphones in order to provide an instant diagnosis to diabetic people residing in re-\nmote areas. In this paper, inception based convolutional neural network and binary\ndecision tree-based ensemble of classiﬁers have been proposed and implemented\nto detect and classify diabetic retinopathy. The proposed method was further im-\nported into a smartphone application for mobile-based classiﬁcation, which pro-\nvides an ofﬂine and automatic system for diagnosis of diabetic retinopathy.\n1 I NTRODUCTION\n1.1 D IABETIC RETINOPATHY DIAGNOSIS\nDiabetic Retinopathy (DR) is a retinal complication caused when retinal blood vessels are damaged\nby diabetes. Signs of DR start with microaneurysms, which are small red spots that appear when\nthere is a blood escape from retinal blood vessels. If microaneurysms are not treated early walls of\ncapillaries may get broken which form hemorrhages. Exudates may appear on the retina if treatment\nof the disease is delayed, and this can lead to permanent vision loss or vision impairment.\nDR diagnosis is clinically performed by ophthalmologists with the help of high-end fundus images\ncapturing devices. In order to capture retinal images, different imaging techniques, such as optical\ncoherence, tomography, and fundus photography, have been used (Salz & Witkin, 2015). All of\nthese techniques come with the challenge of expensive design, deployment, and usage costs. Trained\nprofessionals are needed to use these techniques. In addition to the trained professional need of these\ntechniques, an ophthalmologist or more are required to study and diagnose a fundus image that\nis captured by the imaging methodology. An ophthalmologist usually requires two to seven days\nfor retinal image diagnosis. Diabetes patients that reside in rural and remote areas usually suffer\nfrom delayed diagnosis and treatment of DR because of the expensive deployment of diagnosing\nequipment and shortage of ophthalmologists and health care centers.\nLimited access to point-of-care diagnostic services was identiﬁed as one of the barriers of medical\ndiagnosis in rural areas (Huaynate et al., 2015). Foster & Resnikoff (2005) put four strategies to ﬁght\nthe challenges the diagnoses process of DR faces in order to implement treatment for preventable\nblindness; (1) Creating academic, public and governmental awareness of the effects of blindness and\nvisual loss, and the fact that 75 %of diseases that cause blindness are preventable; (2) Automating and\nmobilizing existing techniques and methods; (3) Implementing district-speciﬁc and country-speciﬁc\nprioritizing strategies of diagnosing and treatment resources for a productive process; (4) Providing\n1arXiv:2004.03408v1  [eess.IV]  7 Apr 2020\n\nPublished as ICCCIS 2019 conference paper at IEEE Xplore\ncomprehensive, maintainable and fair diagnosis services of visual diseases at district level, which\nincludes staff training, distributing diagnosis and treatment resources, and infrastructure, such as\nhealth care center buildings.\nA timely and accurate automatic diagnosis of DR could enable diabetic patients to get treatment for\npreventable visual diseases, thereby avoiding permanent vision loss or impairment. Point-of-care\nDR diagnostic service, which aims to diagnose DR instantly at a patients place, is achieved in this\npaper using a smartphone for data collection and trained model for detection.\n1.2 A NNOTATED TRAINING DATA\nOne of the main issues with incorporating deep learning in medical image analyses is the shortage\nof available annotated training dataset (Miotto et al., 2017)(Razzak et al., 2018). Transfer learning\ntechniques have gained wider acceptance because of the unavailability of enough annotated training\ndata in the design and training of deep convolutional neural network models (Erhan et al., 2010)(Lit-\njens et al., 2017). In Altaf et al. (2019), annotated training data insufﬁciency was identiﬁed as the\nmain challenge of applying deep learning models in the healthcare automation industry. Further-\nmore, Altaf et al. (2019) recommended that methods that exploit deep learning using reduced data\nneed to be devised and implemented. We have combined inception module based convolutional\nneural networks with a binary tree-based ensemble of classiﬁers to increase the performance of our\nproposed neural network model with limited training data.\nThis paper is structured into ﬁve sections. Section 2 presents a review of related works. The proposed\nmethodology and implementation are discussed in Section 3. Results and discussions are presented\nin Section 4. Lastly, we conclude in Section 5.\n2 R ELATED WORK\nAlthough the literature of automated DR detection and classiﬁcation contains various works, the\nmethods employed can be generally classiﬁed into two, which are feature extraction based and\nimage-level based classiﬁcations. In order to provide an onsite diagnosis of DR, mobile detection\nworks have also been proposed and implemented. Deep learning models such as Convolutional\nNeural Networks (CNN) are usually used to classify fundus images. A fundus images dataset that\nis uploaded to the Kaggle website for DR detection competition (California-Healthcare-Foundation,\n2015) has been extensively used in the image level DR classiﬁcation literature. End-to-end approach\nhas been used to train a deep learning model from scratch. In order to avoid the cost of training,\ntransfer learning has also been used.\nIn multi-class classiﬁcation, DR has been classiﬁed into one of ﬁve stages, which are normal, mild,\nmoderate, severe, and proliferative stages, as proposed by Wilkinson et al. (2003). In the following\nsubsections, different works that have been performed in detecting DR will be reviewed.\n2.1 F EATURE EXTRACTION BASED CLASSIFICATION OF DIABETIC RETINOPATHY\nLesions of DR such as macular edema, exudates, microaneurysms, and hemorrhages have been auto-\nmatically identiﬁed, segmented and detected in order to classify DR. End-to-end and transfer learn-\ning of Convolutional Neural Networks (CNN) and Fully Convolved Residual Networks (FCRN)\nhave been employed for classifying the extracted lesions. Table A.1 (See Appendix A) presents a\nsummary of lesion detection based approaches for detecting DR.\n2.2 I MAGE LEVEL CLASSIFICATION OF DIABETIC RETINOPATHY\nIn image level-based classiﬁcation of DR from fundus images, there is no need to segment and\nextract lesions. The detection is performed on the whole fundus image. Table A.2 (See Appendix\nA) summarizes the image level DR detection literature.\n2\n\nPublished as ICCCIS 2019 conference paper at IEEE Xplore\n2.3 M OBILE CLASSIFICATION OF DIABETIC RETINOPATHY\nOne of the strategies suggested by Foster & Resnikoff (2005) for prevention of treatable blindness\nwas the distribution of maintainable and unbiased eye care services at the district level. Tele-retina\nhas been implemented to capture retinal images by non-experts from remote areas and transferring\nto the ophthalmic cente...	all-MiniLM-L6-v2	completed	2025-08-03 22:04:01.534824+00	2025-08-03 22:04:01.534824+00	\N	\N	\N
97a9fdeb-70fe-4767-af62-a54469f4804e	135598cf-16f6-46c7-948a-db8275485a68	all-MiniLM-L6-v2	\N	\N	\N	2025-08-03 22:04:29.13301+00	2025-08-03 22:04:29.13301+00	[-0.006043,-0.069522,0.027808,0.008181,0.055268,-0.009138,0.048912,0.052391,-0.034881,-0.024801,-0.042684,-0.028054,-0.017036,0.05047,-0.106812,-0.077928,-0.003541,0.009612,-0.064297,-0.012765,0.075012,0.006008,-0.023876,-0.03912,0.028579,-0.029783,0.051601,-0.057717,-0.03232,-0.023994,-0.002811,0.025398,-0.001664,0.074844,-0.066344,0.064519,-0.020593,-0.013112,-0.06779,-0.051759,0.014091,-0.005751,-0.019774,0.036225,0.169507,0.015612,-0.024703,0.036954,0.072797,-0.003981,-0.069599,-0.032492,-0.002916,0.025301,0.03811,0.028591,-0.072224,-0.009409,-0.008011,-0.001674,0.023858,-0.052384,0.009176,-0.017591,-0.014145,-0.017494,0.016996,-0.03731,0.039581,-0.044662,-0.013452,0.117065,-0.016386,0.022435,-0.045799,0.021126,0.05177,0.017199,0.038141,-0.053166,0.102761,0.075666,0.100081,0.001723,0.104,0.049664,-0.027919,-0.00072,-0.046618,-0.062256,0.015836,0.011218,-0.0891,0.018321,-0.026967,0.006954,-0.018357,-0.111238,-0.033465,0.082653,-0.039338,-0.064852,0.054141,-0.002305,-0.037298,0.03743,0.109113,0.042806,0.100648,-0.0376,0.057192,0.055807,0.022753,-0.017923,-0.025251,0.040644,-0.057458,-0.017933,0.121386,0.008036,-0.088065,-0.033225,0.026157,-0.071943,0.066956,0.058938,-0.032012,0,-0.007077,0.007985,0.007681,-0.065026,0.05832,-0.054766,0.002921,0.080754,-0.040654,-0.041679,-0.068825,-0.043658,-0.058817,0.063695,0.022646,-0.028473,0.060128,0.04352,0.026163,-0.035627,-0.077373,-0.055748,0.045679,-0.0391,-0.021049,0.033874,0.06768,0.016533,0.0677,0.017727,-0.042256,0.097219,0.071132,-0.006314,-0.015091,-0.040182,0.018387,0.047668,0.04251,-0.045766,-0.018572,0.091861,-0.006903,-0.059546,0.00012,-0.003038,0.043858,0.086871,-0.065809,0.032975,-0.003448,-0.047254,-0.005463,-0.092543,-0.017184,0.033,-0.000753,0.037535,0.066512,0.003407,-0.004027,0.012289,-0.022452,0.08136,-0.078935,-0.075896,0.030613,0.041692,-0.035251,0.024491,-0.014069,0.047816,-0.010128,-0.067309,0.046229,0.057216,0.016792,-0.000256,-0.007126,0.025683,-0.007974,0.132972,0.038395,-0.04576,-0.081419,0.058415,0.020696,0.023894,0.016965,-0.05604,0.001918,0.048693,0.003997,-0.029996,-0.014269,-0,-0.019787,0.085061,-0.052891,0.024517,-0.001596,-0.040194,0.025725,-0.026328,0.077483,-0.052534,0.088081,-0.047769,-0.015243,-0.045005,0.019564,-0.024373,-0.165358,0.020413,-0.064017,0.002549,-0.013223,0.089179,-0.089635,0.007831,-0.016338,0.035387,0.013445,0.110534,-0.082562,-0.040437,0.031755,-0.002313,-0.085021,0.031255,0.004258,0.018516,-0.008525,-0.103376,-0.061083,0.064751,0.093805,0.06207,-0.063169,-0.031419,0.016899,-0.047165,0.055307,-0.001168,0.040064,0.054253,-0.042436,-0.010384,-0.04835,0.038894,-0.021324,-0.000493,0.004134,0.072438,-0.001298,0.027472,-0.081671,-0.167886,-0.020718,0.020575,0.002975,0.015875,0.048249,0.091358,0.075287,0.086275,-0.037028,0.01322,-0.049864,0.024366,-0.012331,-0.070677,-0.057541,0.035723,-0.018321,0.001847,0.04175,-0.095763,-0.026771,0.099031,0.053402,0.024242,0.037665,-0.043456,0.069516,-0.006275,-0.107628,0.013383,-0.056634,-0.025223,-0.037936,-0,0.007228,0.000543,-0.040444,0.017159,0.011986,-0.098868,-0.063372,0.122892,0.007371,-0.067667,-0.016947,-0.00106,-0.075783,-0.084496,-0.014323,0.011121,0.017801,0.081478,0.00534,0.039861,0.024193,-0.024872,0.012922,0.001439,0.008856,-0.108565,-0.046037,0.056016,-0.01679,-0.053744,0.039849,0.022883,0.067508,0.022343,0.023132,0.052102,-0.020067,0.069479,0.016987,0.0763,-0.039492,0.02193,0.024708,-0.013784,-0.081322,-0.054517,0.127618,-0.029017,0.008932,-0.040133,-0.050516,0.007485,0.003371,0.034418,-0.048919,-0.059436,0.005045,-0.04109,-0.033345,0.063915,0.000877,-0.01247,-0.04525,-0.031366]	Automated Diabetic Retinopathy Grading using Deep Convolutional Neural Network Saket S. Chaturvedi*, Kajol Gupta, Vaishali Ninawe, Prakash S. Prasad* Department of Computer Science & Engineering, Priyadarshini Institute of Engineering & Technology, Nagpur, India Email: saketschaturvedi@gmail.com, prakashsprasad@gmail.com ABSTRACT Diabetic Retinopathy is a global health problem, influences 100 million individuals worldwide, and in the next few decades, these incidences are expected to reach epidemic proportions. Diabetic Retinopathy is a subtle eye disease that can cause sudden, irreversible vision loss. The early-stage Diabetic Retinopathy diagnosis can be challenging for human experts, considering the visual complexity of fundus photography retinal images. However, Early Stage detection of Diabetic Retinopathy can significantly alter the severe vision loss problem. The competence of computer-aided detection systems to accurately detect the Diabetic Retinopathy had popularized them among researchers. In this study, we have utilized a pre-trained DenseNet121 network with several modifications and trained on APTOS 2019 dataset. The proposed method outperformed other state-of-the-art networks in early-stage detection and achieved 96.51% accuracy in severity grading of Diabetic Retinopathy for multi-label classification and achieved 94.44% accuracy for single-class classification method. Moreover, the precision, recall, f1-score, and quadratic weighted kappa for our network was reported as 86%, 87%, 86%, and 91.96%, respectively. Our proposed architecture is simultaneously very simple, accurate, and efficient concerning computational time and space. Keywords: Deep Learning, Diabetic Retinopathy, DenseNet network, Fundus Photography, Computer-aided diagnosis. 1. INTRODUCTION The incidence of vision loss due to Diabetic Retinopathy is on the rise, and in the next few decades, these incidences are expected to reach epidemic proportions globally. Since 1980, the cases of diabetes prevalence have quadrupled [1], [2]. The visual impairment and blindness estimates for Diabetic Retinopathy increased by 64% and 27% between 1990 and 2010, respectively [3].  In 2017,  425 million people worldwide were reported with diabetes, and this number is estimated to increase to 642 million by 2040 [4]. It is estimated that nearly every patient with type-1 diabetes and 60% of patients with type-2 diabetes would develop Diabetic Retinopathy in the first 20 years of diabetes [5], [6].  Diabetic Retinopathy (DR) is the most mundane and subtle microvascular complication of diabetes, resulting in a sudden loss of vision. Diabetic Retinopathy often remains undetected until it progresses to an advanced vision-threatening stage as this complicated problem can only be noticed when the tiny blood vessels in the retina begin to damage. This tiny blood vessel causes the blood flow, and fluid present in the retina results in forming features. After the disease starts growing to the next level, oxygen enters in between the retina and clouding vision because of the generation of new blood vessels. In the case of diabetic patients, it is essential to conduct regular screening to track the growth of DR [7] among four severity levels: Normal, Mild, Moderate, Severe, and Proliferative\n\nDiabetic Retinopathy. The most dangerous stage of Diabetic Retinopathy is the proliferative DR in which the likelihood of blood leaking is at a peak, causing permanent vision loss. \n Figure 1. The fundus photography images from APTOS2019 Kaggle’s dataset at each of the Normal, Mild, Moderate, Severe, and Proliferative Diabetic Retinopathy severity levels. The current state of Diabetic Retinopathy screening in the real world is based on the assessment of color fundus photography (see Figure 1), which is induced by an Ophthalmologist. The fundus photography leaves a large proportion of patients undiagnosed and therefore receiving medical help too late, owing to low adherence and access to retina screening visits [8]. In-person expert examinations are impractical and unsustainable, given the pandemic size of the diabetic population [9]–[11]. However, it is time-consuming and resource-demanding to grade the images manually. Notwithstanding, early detection and prevention of DR progression are essential to mitigate the rising threat of DR.  The presence of an automated or computer-aided system can make it very easy for a specialist to observe the retina of diabetic patients clearly [12]. Artificial intelligence (AI) may offer a solution to this conundrum. Deep Learning (DL), and correctly, Deep Convolutional Neural Networks (DCNNs) [13], can be used for an end-to-end assessment of raw medical images to produce a target outcome prediction. The diagnostic use of DCCN algorithms is already spreading in various healthcare areas [14],[15], such as radiology, dermatology [16], and pathology [17]. In ophthalmology, ground-breaking work has recently been conducted on the automation of DR grading [18]–[20]. 2. RELATED WORKS The computer-aided detection systems capability to accurately detect the grades of Diabetic Retinopathy had made them popular among researchers. In the last ten years, numerous research work focusing on the development of Computer-Aided systems to automatically detect Diabetic Retinopathy using traditional machine learning algorithms were recorded.  Quellec et al. [21] used a traditional KNN algorithm with optimal filters on two classes to achieve an AUC of 0.927.  Also, Sinthanayothin et al. [22] proposed an automated Diabetic Retinopathy detection system on morphological features using the KNN algorithm and obtained sensitivity and specificity of 80.21% and 70.66%, respectively. Further, In the paper [23], three classes of Diabetic Retinopathy were classified using Neural Network. They classified mild, moderate, and severe stages of Diabetic Retinopathy with an accuracy of 82.6%, 82.6%, and 88.3%, respectively. Larsen et al. [24] demonstrated an automatic diagnosis of Diabetic Retinopathy in fundus photographs with a visibility threshold. They reported an accuracy of 90.1% for true cases detection and 81.3% for the detection of the false case. Agurto et al. [25] utilized multi-scale Amplitude Modulation and Frequency Modulation based decomposition to distinguish between Diabetic\n\nRetinopathy and normal retina images. In [26], the authors reported an area under ROC of 0.98 for Texture features and accuracy of 99.17% for two-class classification by using Wavelet transform with SVM. Jelinek et al. [27] proposed an automated Diabetic Retinopathy detection by combining the works of Spencer [28] and Cree [27] system, which achieved a sensitivity of 85% and specificity of 90%. Abràmo et al. [29] developed the Eye-Check algorithm for automated Diabetic Retinopathy detection. They detected abnormal lesions with an AUC of 0.839. Dupas et al. [30] developed a Computer-Aided Detection system with a KNN classifier to detect Diabetic Retinopathy with a sensitivity of 83.9% and specificity of 72.7%.  Acharya et al. [31] classified five classes using SVM classifier on the bi-spectral invariant features to achieve sensitivity, specificity, and accuracy of 82%, 86%, and 85.9%, respectively. They also worked utilizing four features and achieved a classification accuracy of 85%, sensitivity of 82%, and specificity of 86%. Roychowdhury et al. [32] proposed a two-step classification approach. In the first step, the false positives were removed. Later, GMM, KNN, and SVM were utilized for the classification task. They reported a sensitivity of 100%, a specificity of 53.16%, and AUC of 0.904.   Deep learning algorithms have become popular in the last few years. Kaggle [33] has launched several competitions focusing on automated grading of Diabetic Retinopathy detection. Pratt et al. [34] introduced a CNN based method, which even surpassed human experts in the classification of advanced stage Diabetic Retinopathy. Kori et al. [3...	all-MiniLM-L6-v2	completed	2025-08-03 22:04:29.13301+00	2025-08-03 22:04:29.13301+00	\N	\N	\N
a3abe348-2721-4f8f-a49e-af06b0e88e66	d28b3211-9f93-4271-8d5b-680807b486e0	all-MiniLM-L6-v2	\N	\N	\N	2025-08-03 22:04:56.161548+00	2025-08-03 22:04:56.161548+00	[-0.053202,-0.003453,-0.013101,0.002751,0.042872,-0.01174,0.101328,0.072018,-0.007718,0.006758,-0.085011,-0.041652,0.004927,0.061936,-0.134479,-0.094748,-0.017673,0.004145,-0.035845,-0.009157,0.066517,0.047796,-0.026153,0.003872,-0.012712,-0.014498,0.09096,-0.017947,-0.012928,-0.039628,0.015948,-0.017014,0.007216,0.032403,-0.091345,0.020201,-0.038208,0.047204,-0.152672,-0.018954,-0.024417,-0.022377,-0.078738,0.04214,0.142863,0.018278,-0.031259,0.033148,0.038103,0.000509,-0.121843,-0.045442,-0.035603,0.005934,-0.017533,0.044041,-0.037998,-0.039938,-0.018224,-0.005938,0.038646,-0.086635,0.039646,-0.00774,0.011162,-0.035163,0.033384,-0.051717,0.03528,-0.054171,-0.06215,0.080884,-0.004723,0.067895,3.1e-05,-0.00649,0.002649,0.013903,0.080682,0.008145,0.051814,0.07855,0.040685,0.018571,0.120046,0.031398,-0.050677,-0.038623,-0.006316,-0.071949,0.008635,-0.014045,-0.051811,-0.02569,-0.013343,0.008439,0.067845,-0.049063,0.049316,0.079104,-0.071421,-0.014154,0.05949,0.013637,-0.047108,-0.031254,0.070267,0.015607,0.105493,-0.053034,0.011359,0.070571,-0.012687,-0.05199,-0.038476,0.045963,-0.074605,0.012434,0.132966,0.048753,-0.061202,-0.028993,0.026738,-0.033302,0.136679,0.109205,-0.035423,0,0.001311,0.022834,0.009227,-0.040713,0.024851,-0.038022,-0.02798,0.052232,0.028022,-0.046298,-0.048493,-0.013188,0.027573,0.10155,0.032512,-0.03108,0.071288,0.062436,-0.016761,-0.031964,-0.037221,-0.025101,0.077815,-0.03189,-0.014493,0.039256,0.017003,0.056726,0.102593,0.029289,0.040017,0.024253,0.0247,-0.020018,0.06648,-0.042073,0.027977,0.031243,0.012741,-0.040889,-0.020794,0.037887,0.020154,-0.081791,0.015499,0.022122,0.015669,0.042523,-0.066795,0.007388,0.011866,-0.039369,-0.010409,-0.028728,-0.00719,0.047716,-0.074235,0.021385,0.03655,-0.009485,-0.004479,0.073486,-0.008518,0.104365,-0.016504,-0.038664,0.078809,-0.010346,-0.016673,-0.003135,-0.007945,0.027716,0.017197,-0.039792,0.039943,0.021061,0.031763,0.056624,0.008691,-0.012239,-0.019378,0.075369,0.010156,-0.075809,-0.046161,-0.002063,0.019709,-0.000675,-0.02082,-0.039443,-0.028149,0.075628,-0.001088,0.013187,0.02581,-0,0.016998,-0.020234,0.014803,-0.002153,0.02667,-0.029795,0.002691,-0.052655,0.068837,-0.139491,-0.0081,-0.01893,0.036321,0.006201,-0.019869,0.056365,-0.111472,0.05347,-0.048997,0.051344,-0.035272,0.122996,-0.052893,-0.054991,0.002406,0.050883,0.010364,0.086928,-0.097784,-0.056755,0.01705,-0.011507,-0.12147,-0.030312,-0.076651,0.008942,-0.05887,-0.069873,-0.062846,0.116021,0.067974,0.057126,-0.070326,-0.063703,0.037545,-0.058549,-0.005401,0.034458,0.07199,-0.005436,-0.043972,0.002888,-0.067031,0.001354,-0.063543,0.034247,0.043473,0.041022,0.002273,0.086628,-0.043058,-0.107963,0.011936,0.087326,0.031933,0.03093,0.070643,0.035471,0.068965,0.027092,0.022086,-0.039551,-0.065431,0.014591,0.016089,-0.060732,-0.058747,0.025157,-0.069195,0.006109,0.024346,-0.136289,-0.002789,0.113089,-0.03756,0.010116,0.047868,-0.096247,0.042821,-0.060754,-0.057228,-0.021434,-0.054594,0.046445,-0.008376,-0,0.02996,-0.018019,-0.015499,-0.042269,0.026083,-0.070257,-0.110594,0.086298,-0.037638,-0.042096,0.038429,-5.2e-05,-0.05287,-0.033112,0.058769,-0.012199,0.026925,0.091728,-0.045607,0.023521,0.02996,-0.076188,0.053388,0.015317,0.015826,-0.086325,0.004864,-0.010351,0.008289,-0.011066,-0.023972,0.076799,0.097751,0.095389,0.02738,0.024723,-0.041682,0.00316,-0.02994,0.06567,-0.036527,0.009478,-0.005981,0.019185,-0.051593,-0.017267,0.10097,-0.089478,-0.006156,-0.038977,-0.054797,-0.015863,0.033467,0.038422,-0.045512,-0.033478,0.028647,-0.051662,-0.02783,0.019392,0.01849,-0.030381,-0.04046,-0.036583]	Diabetic Retinopathy Detection using Ensemble \nMachine Learning\nIsraa Odeh \nDepartment of Computer Science \nPSUT \nAmman, Jordan \nisr20170294@std.psut.edu.jo\nMouhammd Alkasassbeh \nDepartment of Computer Science \nPSUT \nAmman, Jordan \nm.alkasassbeh@psut.edu.jo\nMohammad Alauthman \nDepartment of Information Security \nUniversity of Petra\nAmman, Jordan \nmohammad.alauthman@uop.edu.jo\nAbstract\n—\nDiabetic\nRetinopathy\n(DR)\nis\namong\nthe\nworld’ s \nleading\nvision\nloss\ncauses\nin\ndiabetic\npatients.\nDR\nis\na \nmicr ovascular\ndisease\nthat\naffects\nthe\neye\nretina,\nwhich\ncauses \nvessel\nblockage\nand\ntherefore\ncuts\nthe\nmain\nsource\nof\nnutrition \nfor\nthe\nretina\ntissues.\nTreatment\nfor\nthis\nvisual\ndisorder\nis\nmost \neffective\nwhen\nit\nis\ndetected\nin\nits\nearliest\nstages,\nas\nsever e\nDR \ncan\nresult\nin\nirreversible\nblindness.\nNonetheless,\nDR \nidentification\nrequir es\nthe\nexpertise\nof\nOphthalmologists\nwhich \nis\noften\nexpensive\nand\ntime-consuming.\nTher efore,\nautomatic \ndetection\nsystems\nwere\nintroduced\naiming\nto\nfacilitate\nthe \nidentification\nprocess,\nmaking\nit\navailable\nglobally\nin\na\ntime\nand \ncost-efficient\nmanner .\nHowever ,\ndue\nto\nthe\nlimited\nreliable \ndatasets\nand\nmedical\nrecords\nfor\nthis\nparticular\neye\ndisease,\nthe \nobtained\npredictions’\naccuracies\nwere\nrelatively\nunsatisfying\nfor \neye\nspecialists\nto\nrely\non\nthem\nas\ndiagnostic\nsystems.\nThus,\nwe \nexplor ed\nan\nensemble-based\nlearning\nstrategy ,\nmerging\na \nsubstantial\nselection\nof\nwell-known\nclassification\nalgorithms\nin \none\nsophisticated\ndiagnostic\nmodel.\nThe\nproposed\nframework \nachieved\nthe\nhighest\naccuracy\nrates\namong\nall\nother\ncommon \nclassification\nalgorithms\nin\nthe\narea.\n4\nsubdatasets\nwere \ngenerated\nto\ncontain\nthe\ntop\n5\nand\ntop\n10\nfeatur es\nof\nthe \nMessidor\ndataset,\nselected\nby\nInfoGainEval.\nand \nWrapperSubsetEval.,\naccuracies\nof\n70.7%\nand\n75.1%\nwere \nachieved\non\nthe\nInfoGainEval.\ntop\n5\nand\noriginal\ndataset \nrespectively.\nThe\nresults\nimply\nthe\nimpressive\nperformance\nof\nthe \nsubdataset,\nwhich\nsignificantly\nconduces\nto\na\nless\ncomplex \nclassification\nprocess\nwhen\ncompared\nto\nthe\noriginal\ncomplete \nMessidor dataset.\nKeywords—\nDiabetic\nRetinopathy ,\nEnsemble\nlearning,\nMachine \nlearning\nI.\nINTRODUCTION\nDiabetic\nRetinopathy\nis\na\ndiabetes\ncomplication\nthat \ndamages\nthe\nlight-sensitive\nretina\ntissues\nand\nblood\nvessels \ndue\nto\nhigh\nblood\nsugar\nrates,\nmacular\nchanges\nsuch\nas \nyellowish\nspots,\naneurysms\n(an\nincrease\nof\nthe\nmicrovascular \nthickness\nor\n“ballooning”\nin\nthe\nretina),\nand\nhemorrhage \n(blood\nescaping\nfrom\nblood\nvessels)\nare\nconsidered\nthe\nmost \ncommon implications of DR.\nMacular\nirregularities\nin\ndiabetic\npatients\nwere\nfirst \ndetected\nin\n1856\nby\nEduard\nJaeger.\nHowever,\nthose\nwere\nnot \nconfirmed\nto\nbe\nrelated\nto\ndiabetes\nuntil\n1872,\nwhen\nJaeger \nfirst\nprovided\na\nhistopathologic\nproof\nof\n“cystoid \ndegeneration\nof\nthe\nmacula”\nin\ndiabetic\npatients.\nSeveral \nstudies\nwere\ncarried\nin\nthe\nfollowing\nyears\nleading\nto\nthe \ndiscovery\nof\nProliferative\nDiabetic\nRetinopathy\nby\nWilhelm \nManz in 1876 [1].\nAs\nstated\nby\nMayo\nClinic\n[2],\ncommon\nsymptoms\nof\nDR \ninclude\nspots\nin\nvision,\nblurred\nor\nfluctuated\nsight,\ncolor \nimpairment,\nand\nin\nsome\nsevere\ncases,\na\ncomplete\nvision\nloss \nin\none\nor\nboth\neyes.\nIn\nthe\nlong\nterm,\nhigh\nblood\nsugar\nrates\ncause\nblockage\nin\nthe\nmicrovessels\nof\nthe\nretina,\nwhich\nare \nvery\nimportant\nfor\nnourishing\nthe\nretina\ntissues,\ntherefore, \nthe\neye\nattempts\nto\ngrow\nnew\nvessels\nto\nsupply\nthe\nretina \nwith\nthe\nneeded\nnutrients\nand\noxygen,\nhowever,\nthese \ngenerated\nvessels\nare\nweak\nand\nlikely\nto\nsuffer\nblood\nleakage \nforming\na\nhemorrhage\nin\nthe\nretina.\nAccording\nto\nthe \nseverity\nof\nthe\ndetected\nsymptoms,\nDR\nis\ngraded\ninto\none\nof \n3 stages; Mild, Moderate, and Proliferative DR (PDR).\nIn\nmany\ncases,\na\nfast\nclinical\ncheck\nand\ndecision\nmust\nbe \nmade\nfor\ndifferent\nreasons,\nsuch\nas\na\nlarge\nnumber\nof \npatients\nin\na\nspecific\nfacility,\nor\nan\nurgent\nand\ncritical\npatient \ncondition.\nMoreover,\naffordable\ntreatment\nshould\nbe \nprovided\nto\nall\npatients,\nhowever,\nin\nmany\ndeveloping \ncountries,\npatients\nare\nnot\nprovided\nwith\nadequate\nhealth\ncare \nnor\naffordable\ntreatment.\nHence,\nmany\nunderprivileged \npatients\nare\nat\na\nvery\nhigh\nrisk\nof\nlosing\ntheir\nsight\nowing\nto \nthe\nabsence\nof\nreasonable\nhealthcare.\nConsequently,\nvarious \nArtificial\nIntelligence\nalgorithms\nwere\napplied\nto\nproduce \nefficient\nmedical\ndecision-making\nsystems,\nsuch\nas\nin\nExpert \nSystems,\nNatural\nLanguage\nProcessing\n(NLP)\nand\nother \nmachine\nlearning\napplications,\nleading\nto\nthe\nfirst\nexpert \nsystem\nspecialized\nin\nmedical\npractices\ncalled\nMYCIN,\nthis \nrule-based\nprediction\nmodel\nwas\nintroduced\nin\nthe\nearly \n1970s\nafter\nalmost\n6\nyears\nof\ndevelopment\nat\nStanford \nUniversity,\nUSA\n[3].\nMany\nother\nArtificial\nIntelligence \napplications\nwere\nemployed\nin\nvarious\nhealthcare\nsectors, \nlike\nRadiology,\nScreening,\nand\nDisease\nDiagnosis.\nSeveral \nhospitals\nincluding\nMayo\nClinic,\nUSA,\nand\nthe\nNational \nHealth\nService,\nUK\nhave\ndeveloped\ntheir\nown\nIntelligent \nsystems\n[4,5],\nas\nwell\nas\nGoogle\n[6]\nand\nIBM’s\n[7] \ncontributions to healthcare technology advancements.\nIn\nthis\nresearch,\nwe\nhave\ndeveloped\na\nmodern\nautomatic \ndetection\nmodel\nfor\nDiabetic\nRetinopathy,\nconcentrating\non \nutilizing\nthe\nmost\nefficient\nensemble\nof\nmachine\nlearning \nalgorithms\nin\norder\nto\nobtain\na\nhighly\naccurate\ndiagnosis. \nMoreover,\nin\nthe\npresent\nensemble-based\nframework,\nas \nelucidated\nin\nthe\nrest\nof\nthis\ndocument,\nwe\nhave\nalso \nconsidered\nachieving\nexcellent\nprecision\nwhile\npreserving\nan \nefficient performance with minimal time and storage\ncosts.\nThe\nremainder\nof\nthis\npaper\nis\norganized\nas\nfollows; \nsection\n2\npresents\na\nliterature\nreview\nand\na\ndiscussion\nof \npreviously\nreported\nwork\non\nDiabetic\nRetinopathy\nautomatic \ndetection.\nIn\nsection\n3,\na\ndetailed\ndescription\nof\nthe\nproposed \ndiagnostic\nmodel\nis\nprovided,\nfollowed\nby\nthe\nexperimental \ndataset\nand\nmethods\nused\nin\nthis\nstudy.\nThe\nfinal\nsection \nconcludes\nand\nsummarizes\nthe\nwork\nalong\nwith\nthe\nauthors’ \nopinion on future work and directions.\n\nII.\nRelated Work\nNumerous\nstudies\nhave\nbeen\ncarried\nout\non\nthe \nautomated\nidentification\nof\nthe\nDR,\nits\nreliability,\nefficiency \nand\nmaintainability.\nIn\n2006,\nJelinek\net\nal\n.\n[8]\nproposed\na\nDR \ndetection\nsystem\nfully\nreliant\non\ndetecting\nred\nlesions\nin\nthe \nretina\nusing\nimage\nprocessing\nand\nanalysis.\nFollowed\nby \nAbramoff\net\nal.\n[9]\nin\n2010,\nand\nAntal\nand\nHajdu\net\nal\n.\n[10] \nmodel\nin\n2012\ndepending\non\nthe\nsame\nprimary\nlesion\nJelinek \nused.\nHowever,\nthe\npreviously\nproposed\nsystems\nhaven’t\nmet \nthe\naccuracy\nand\nsensitivity\nlevels\nophthalmologists \nrequired.\nFurther\nresearch\nwas\nconducted\nthroughout\nthe\nfollowing \nyears.\nOne\nof\nthe\nideas\nto\nimprove\nthe\nDR\nidentification \nalgorithms\nwas\nto\ninclude\nmore\nfeatures\nthat\ncan\nbe\nextracted \nfrom\na\nretina\nfunduscopy.\nFor\ninstance,\nimage\nquality\nwas \nproven\nto\nhave\na\nsignificant\neffect\non\nthe\nfinal\nprediction \n[11],\nretinal\nimages\nwith\nlow\nresolution\nwill\nprobably \nincrease the chance of developing FP and FN predictions.\nAntal\nand\nHajdu’s\n[12]\nproposed\nsystem\nmerges\nseveral \ncomparison\ncomponents\nused\nin\nprevious\nworks;\nImage \nquality,\nLesion-specific\ncomponents,\nMulti-scale\nAM/FM \nbased\nfeature\nextraction,\nPre-screening\nand\nAnatomical \ncomponents\n(Macula\nand\nOptic\nDisk\ndetection)\nin\nan \nensemble-based\ndecision-making\nsystem,\nthis\nwas\ndone\nby \ntraining\nseveral\nwell-known\nclassifiers\nalong\nwith\nenergy \nfunctions\nand\nfusion\nstrategies\nfor\nensemble\nselection. \nBasically,\nany\nclassifier\nthat\nproduces\na\nhigher\noverall \naccuracy\nis\nincluded\nin\nthe\nsystem,\notherwise\nexcluded.\nThe \nauthors\nrecommended\nbackward\nensemble\nsearch \nmethodology\nusing\naccuracy\nand\nsensitivity\nenergy \nfunctions,\nwhich\nfirst\nconsiders\nall\nclassifiers\nare\npart\nof\nthe \nensemble,\nthen\neach\nclassifier\nis\ntested\nto\nbe\nexcluded\nonly\nif \nelimination\ncauses\naccuracy\nto\nincrease.\nAntal\nand\nHajdu’s \nensembled\nsystem\nachieved\nan\noutstanding\naccuracy\nof\n90%, \nSensitivity\nof\n90%,\nand\n91%\nSpecificity\nin\nboth\ndisease\nand \nno-disease settings.\nGargeya\nand\nLeng’s\n[13]\nproposed\nalgorithm\nis\nmainly \nconstructed\nof\nDeep\nconvolutional\nneural\nnetworks ...	all-MiniLM-L6-v2	completed	2025-08-03 22:04:56.161548+00	2025-08-03 22:04:56.161548+00	\N	\N	\N
0640c1bd-b76f-4d5f-83ce-b2ad345912b6	b3251a67-101b-40ab-a1e7-551c18ccbecb	all-MiniLM-L6-v2	\N	\N	\N	2025-08-03 22:05:19.249977+00	2025-08-03 22:05:19.249977+00	[-0.034333,-0.065676,0.04596,0.003546,0.086712,0.004455,0.057348,-0.011107,-0.00125,-0.041792,-0.00542,-0.026253,-0.012719,0.088978,-0.086966,-0.088057,0.067387,0.055189,-0.120359,0.074336,0.079048,0.05311,-0.000877,-0.015492,0.02085,-0.032963,0.095788,-0.031318,-0.013393,-0.056061,-0.001443,0.019027,-0.052988,0.042516,-0.05992,-0.004904,-0.01845,0.064486,-0.086231,0.004117,0.063116,0.027152,0.018887,0.050749,0.115713,-0.019699,-0.039363,-0.006448,0.043436,0.024916,-0.063561,0.016126,-0.049039,0.066156,0.035036,0.05525,0.027432,-0.059984,-0.01195,0.021988,0.025637,-0.044782,-0.002095,-0.018314,-0.044986,0.039057,-0.01377,-0.025107,0.034234,-0.061001,0.008556,0.094801,-0.032025,0.037093,0.013905,0.008245,0.02015,0.017335,0.081934,-0.092591,0.053706,0.055456,0.107142,-0.031047,0.172126,0.056297,-0.037544,-0.002936,-0.007009,-0.033442,-0.045845,-0.035309,-0.065878,0.001812,-0.009631,-0.002845,0.033828,-0.09354,0.006871,0.085885,-0.063032,0.002786,0.023323,-0.025915,0.000543,-0.013849,0.077807,0.061884,0.083429,-0.081193,0.03837,0.046479,-0.001638,-0.009753,-0.038301,-0.064045,0.039856,-0.034529,0.052397,0.007987,-0.087616,0.044183,0.017427,-0.044955,0.023037,0.015971,-0.041674,0,-0.000539,-0.036882,0.06961,-0.008188,0.033785,-0.064414,-0.11862,0.04803,0.017109,-0.010081,-0.071882,0.007934,-0.049942,0.038531,0.090794,0.010994,-0.001581,0.02721,0.055948,-0.010007,-0.059463,-0.044802,-0.000714,-0.033743,-0.02657,0.0536,0.040826,0.002489,0.058602,0.031222,-0.073769,0.087542,0.032828,-0.064833,0.034001,-0.075037,0.009156,0.026097,0.050077,-0.065828,-0.019876,0.024388,-0.017255,-0.029922,-0.01612,-0.009303,0.072617,0.032352,-0.074232,-0.046059,0.005988,-0.0374,0.025478,-0.05068,-0.065516,-0.007103,-0.045897,0.049575,0.034003,0.035392,0.074215,0.079691,-0.003307,0.109946,-0.009929,-0.052521,-0.042072,-0.02137,-0.02811,-0.047924,0.037323,0.023846,-0.019361,-0.074761,0.030466,0.024589,0.003029,-0.001019,-0.017893,-0.015705,0.021767,0.036042,0.041192,-0.060221,-0.059558,0.043866,0.01097,0.000631,-0.044761,-0.084147,-0.031228,0.048712,-0.03332,-0.029931,0.056866,-0,-0.039468,0.080196,0.032017,-0.038955,0.024444,-0.062444,-0.031532,0.015916,0.052863,-0.097278,0.010098,-0.03572,0.015169,-0.051726,-0.029759,0.027687,-0.114247,0.002283,-0.083771,0.005889,0.002835,0.0531,-0.110382,0.025857,-0.025529,0.099292,0.029872,0.1293,-0.048666,-0.046904,-0.034361,0.02544,-0.052463,-0.002594,-0.067179,0.038765,-0.048768,-0.032863,-0.081761,0.096086,0.072626,0.011908,-0.102577,-0.009125,0.024081,-0.047699,0.020231,0.027777,0.049697,0.055364,-0.094751,0.024631,-0.068828,0.061007,-0.093582,-0.005896,-0.003995,0.012997,0.037588,0.070202,-0.052983,-0.109121,-0.034023,0.028641,-0.019315,-0.026672,0.014199,0.058991,0.055121,0.053942,0.038209,0.00263,-0.004977,-0.033028,-0.009571,-0.058251,0.023725,0.04386,0.017061,-0.005112,0.0392,-0.142328,-0.000329,0.116179,0.040437,0.036049,0.078838,-0.107572,0.078186,-0.029964,-0.079643,0.024946,-0.08516,-0.005782,-0.013051,-0,0.042592,0.019692,0.00506,0.020209,0.052136,-0.029898,-0.06253,0.119036,-0.027415,0.005449,0.005464,0.014857,-0.004044,-0.09355,-0.031976,0.078005,0.037474,0.112322,-0.013212,0.023109,0.019614,-0.029376,0.071459,0.071945,-0.026528,-0.098215,-0.06004,-0.000281,0.015206,0.002739,0.070918,0.061969,0.068135,0.02161,-0.006341,0.058656,-0.002934,0.012845,-0.006619,0.015069,-0.079155,-0.008528,-0.051003,0.034479,-0.006411,-0.022879,0.123124,-0.024666,0.064779,0.027979,-0.028306,0.001933,0.022731,0.040543,-0.040898,-0.060829,0.01466,-0.047874,-0.025519,0.041877,0.018169,-0.025574,-0.07269,0.007034]	DISTRIBUTIONAL SHIFTS IN AUTOMATED DIABETIC RETINOPATHY SCREENING\nJay Nandy1Wynne Hsu1;2Mong Li Lee1;2\n1School of Computing, National University of Singapore\n2Institute of Data Science, National University of Singapore\nfjaynandy,whsu,leeml g@comp.nus.edu.sg\nABSTRACT\nDeep learning-based models are developed to automatically\ndetect if a retina image is ‘referable’ in diabetic retinopathy\n(DR) screening. However, their classiﬁcation accuracy de-\ngrades as the input images distributionally shift from their\ntraining distribution. Further, even if the input is not a retina\nimage, a standard DR classiﬁer produces a high conﬁdent\nprediction that the image is ‘referable’. Our paper presents\na Dirichlet Prior Network-based framework to address this\nissue. It utilizes an out-of-distribution (OOD) detector model\nand a DR classiﬁcation model to improve generalizability by\nidentifying OOD images. Experiments on real-world datasets\nindicate that the proposed framework can eliminate the un-\nknown non-retina images and identify the distributionally\nshifted retina images for human intervention.\nIndex Terms —Distributional Shift, Dirichlet Prior Net-\nwork, Diabetic Retinopathy Screening, Out-of-distribution\n1. INTRODUCTION\nDiabetic retinopathy (DR) is one of the leading causes of pre-\nventable blindness in the world. It affects diabetic patients\nwithin the ﬁrst two decades of the disease [1]. Vision loss\ndue to diabetic retinopathy is irreversible. Several frame-\nworks are proposed to automate the DR screening process\n[2, 3]. Recently, deep neural network (DNN) based models\nachieve clinically acceptable classiﬁcation accuracy to detect\nreferable DR at lower costs [4, 5]. However, these DNN mod-\nels are sensitive to in-domain training distribution [6, 7, 8, 9,\n10, 11]. Any minor distributional shift leads to over-conﬁdent\npredictions even if they are wrong, producing poor classiﬁca-\ntion performance [12, 13]. Hence, predictive uncertainty esti-\nmation has emerged as a crucial research direction to inform\nabout possible wrong predictions, thus instilling user’s trust\nin deep learning systems [14, 15, 16].\nPredictive uncertainty in a classiﬁcation model can arise\nfrom three sources: model uncertainty, data uncertainty, and\nknowledge uncertainty [14, 12]. Model uncertainty captures\nthe uncertainty in estimating the model parameters, condi-\ntioning on training data [14]. Data uncertainty arises from\nthe natural complexities of the underlying distribution, suchas class overlap, label noise, and others [14]. Knowledge\n(or distributional) uncertainty arises due to the distributional\nshifts between the training and test examples, i.e., the test data\nisout-of-distribution (OOD) [12, 17]. For real-world applica-\ntions, the ability to detect OOD examples can allow manual\nintervention in an informed way.\n(a) In-domain\n (b) Out-of-distribution\nFig. 1 : Illustration of the retina images from different sources.\nTo build an automated DR screening system, we typically\ntrain a deep learning model using a set of pre-collected retina\nimages [4]. We apply standard preprocessing techniques (e.g.,\nimage normalization and data augmentation) to improve their\ngeneralization for unknown test images obtained from the\nsame distribution as the training images. However, these\ntechniques do not generalize a model for the test images that\nare distributionally different from those pre-collected training\nimages. Figure 1 illustrates two retina images, obtained from\ntwo different distributions. Hence, a DR classiﬁcation model\nmay produce incorrect predictions with high conﬁdence for\nunknown OOD images obtained from different distributions.\nRecent works have made signiﬁcant progress to detect\ndistributional uncertainty for unknown OOD test images [17,\n15, 13, 18]. However, these models often fail to detect the\nOOD examples as the out-distribution and in-distribution be-\ncome “alike”. For example, both in-domain and OOD ex-\namples are retinal images, as shown in Figure 1. It leads to\ndegrading the performance of these OOD detection models.\nIn this paper, we focus on the DR screening application.\nWe aim to quantify the distributional shift in an input retina\nimage while maintaining the high classiﬁcation performance.\nOur framework utilizes the state-of-the-art Dirichlet prior net-\nwork (DPN) [19, 18]. We train an OOD detector separately\nfrom the DR classiﬁcation model. We use retina images as in-arXiv:2107.11822v1  [cs.CV]  25 Jul 2021\n\ndomain and natural images as OOD training set for our DR\nclassiﬁer. It also improves their classiﬁcation performance\ncompared to the baseline CNN model. However, it cannot\ndistinguish the out-of-distribution retina images. Hence, we\ntrain a separate OOD detector. Here we use both in-domain\nretina images and OOD images comprising a natural dataset\nand a few retina images obtained from a different distribution.\nExperimental results on multiple real-world datasets\ndemonstrate that our proposed framework effectively detects\nthe OOD retina and non-retina OOD images. We discard the\nnon-retina images and forward the OOD retina images to the\nhuman graders for veriﬁcation. Hence, it leads to a greater\nacceptance of deep learning models for DR screening tasks.\n2. DIRICHLET PRIOR NETWORK\nA Dirichlet Prior Network (DPN) trains a standard neural net-\nwork with a different loss function to represent their predic-\ntions as Dirichlet distributions over the probability simplex\n[19, 18]. It attempts to produce a sharp Dirichlet at one cor-\nner of the simplex when it conﬁdently predicts an in-domain\nexample (see Figure 2(a)). For in-domain examples tending\nto misclassiﬁcation, it should appear as a sharp distribution\nin the middle of the simplex, as shown in Figure 2(b). For\nan OOD example, a DPN attempts to produce a sharp multi-\nmodal Dirichlet, spread uniformly at each corner of the sim-\nplex to indicate their high distributional uncertainty (see Fig-\nure 2(c)) [18, 20]. We observe that the probability densities\nfor Dirichlet distribution in Figure 2(c) are more scattered\nover the simplex compared to that in Figures 2(a) and 2(b).\n(a) Conﬁdent\n (b) Misclassiﬁcation\n (c) Distributional\nFig. 2 : Desired output of a DPN classiﬁer.\nA Dirichlet distribution is parameterized with a vector of\nconcentration parameters =f1;;Kg, as follows:\nDir(j) =(0)QK\nk=1(k)KY\nk=1k1\nk; k>0; (1)\nwhere0=PK\nk=1kis the precision of the distribution.\nA higher precision value leads to a sharper uni-modal\nDirichlet distribution. Consequently, a lower precision pro-\nduces a ﬂatter uni-modal distribution. However, as we further\nuniformly decrease the concentration parameters to lower\nthan1, we obtain a sharp multi-modal distribution with equal\nprobability density at each corner of the simplex (Figure\n2(c)). Hence, for a K-class classiﬁcation problem, we need\nto produce Kpositive values for each class to obtain the\nK-dimensional Dirichlet distribution.A deep neural network (DNN) can be viewed as a DPN\nwhose pre-softmax (logit) output corresponding to the class\nkfor an inputxiszk(x). Then its concentration parameters\nkis given by: k=ezk(x). The expected posterior for class\nlabel!kis given as: p(y=!kjx;) =k\n0=ezk(x)\nPK\nk=1ezk(x);\nwheredenotes the DNN parameters.\nA DPN measures the distributional uncertainty using the\nmutual information (MI) [19], as follows:\nKX\nk=1k\n0\n (k+ 1) (0+ 1)lnk\n0\n(2)\nwhere (:)is digamma function. kis the concentration pa-\nrameters for class k.0=PK\nk=1kis the precision of the\noutput Dirichlet distributions. For a known in-domain image,\na DPN produces a lower MI score to indicate low distribu-\ntional uncertainty. Consequently, it produces a higher MI\nscore for an OOD image.\n3. PROPOSED FRAMEWORK\nOur proposed DPN-based framework for diabetic retinopathy\nscreening utilizes a DR classiﬁer and an OOD detector. We\ntrain the OOD detector separately from the classiﬁer. Fig. 3\npresents an overview of our proposed framework. Given an\ninput image, we pass it to both the OOD d...	all-MiniLM-L6-v2	completed	2025-08-03 22:05:19.249977+00	2025-08-03 22:05:19.249977+00	\N	\N	\N
\.


--
-- Data for Name: papers; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.papers (id, title, date_added, last_modified, pdf_path, bib_path, file_size, mime_type, checksum, private_uploaded, authors, keywords, created_at, updated_at, deleted_at, xml_path, arxiv_id, doi, abstract, safe_title) FROM stdin;
77ec8d85-6e43-4254-aa0e-038b3a585cca	1706.03762v7.pdf	2025-08-03 19:53:00.52139+00	2025-08-03 19:53:00.52139+00	papers/170603762v7pdf-77ec8d85-6e43-4254-aa0e-038b3a585cca.pdf	\N	2215244	application/pdf	18e1b007a1dab45b30cc861ba2dfda25	t	{}	{}	2025-08-03 19:53:00.52139+00	2025-08-03 19:53:00.5697+00	\N	\N	\N	\N	\N	\N
4b830fca-7ca6-44fb-81f2-a1326837d41c	Single-Image Crowd Counting via Multi-Column Convolutional Neural Network	2025-08-03 19:54:48.693937+00	2025-08-03 19:54:48.693937+00	\N	\N	\N	\N	\N	f	{"Yingying Zhang","Desen Zhou","Siqin Chen","Shenghua Gao","Yi Ma"}	{}	2025-08-03 19:54:48.693937+00	2025-08-03 19:54:48.693937+00	\N	\N	\N	https://doi.org/10.1109/cvpr.2016.70	This paper aims to develop a method than can accurately estimate the crowd count from an individual image with arbitrary crowd density and arbitrary perspective. To this end, we have proposed a simple but effective Multi-column Convolutional Neural Network (MCNN) architecture to map the image to its crowd density map. The proposed MCNN allows the input image to be of arbitrary size or resolution. By utilizing filters with receptive fields of different sizes, the features learned by each column CNN are adaptive to variations in people/head size due to perspective effect or image resolution. Furthermore, the true density map is computed accurately based on geometry-adaptive kernels which do not need knowing the perspective map of the input image. Since exiting crowd counting datasets do not adequately cover all the challenging situations considered in our work, we have collected and labelled a large new dataset that includes 1198 images with about 330,000 heads annotated. On this challenging new dataset, as well as all existing datasets, we conduct extensive experiments to verify the effectiveness of the proposed model and method. In particular, with the proposed simple MCNN model, our method outperforms all existing methods. In addition, experiments show that our model, once trained on one dataset, can be readily transferred to a new dataset.	\N
26c4412b-a75a-4852-8b1d-b5164e7059a5	Cross-scene crowd counting via deep convolutional neural networks	2025-08-03 19:54:48.705168+00	2025-08-03 19:54:48.705168+00	\N	\N	\N	\N	\N	f	{"Cong Zhang","Hongsheng Li","Xiaogang Wang","Xiaokang Yang"}	{}	2025-08-03 19:54:48.705168+00	2025-08-03 19:54:48.705168+00	\N	\N	\N	https://doi.org/10.1109/cvpr.2015.7298684	Cross-scene crowd counting is a challenging task where no laborious data annotation is required for counting people in new target surveillance crowd scenes unseen in the training set. The performance of most existing crowd counting methods drops significantly when they are applied to an unseen scene. To address this problem, we propose a deep convolutional neural network (CNN) for crowd counting, and it is trained alternatively with two related learning objectives, crowd density and crowd count. This proposed switchable learning approach is able to obtain better local optimum for both objectives. To handle an unseen target crowd scene, we present a data-driven method to fine-tune the trained CNN model for the target scene. A new dataset including 108 crowd scenes with nearly 200,000 head annotations is introduced to better evaluate the accuracy of cross-scene crowd counting methods. Extensive experiments on the proposed and another two existing datasets demonstrate the effectiveness and reliability of our approach.	\N
a17ce92c-7a86-4b7b-9ec3-faa420c1ec69	Switching Convolutional Neural Network for Crowd Counting	2025-08-03 19:54:48.725861+00	2025-08-03 19:54:48.725861+00	\N	\N	\N	\N	\N	f	{"Deepak Babu Sam","Shiv Surya","R. Venkatesh Babu"}	{}	2025-08-03 19:54:48.725861+00	2025-08-03 19:54:48.725861+00	\N	\N	\N	https://doi.org/10.1109/cvpr.2017.429	We propose a novel crowd counting model that maps a given crowd scene to its density. Crowd analysis is compounded by myriad of factors like inter-occlusion between people due to extreme crowding, high similarity of appearance between people and background elements, and large variability of camera view-points. Current state-of-the art approaches tackle these factors by using multi-scale CNN architectures, recurrent networks and late fusion of features from multi-column CNN with different receptive fields. We propose switching convolutional neural network that leverages variation of crowd density within an image to improve the accuracy and localization of the predicted crowd count. Patches from a grid within a crowd scene are relayed to independent CNN regressors based on crowd count prediction quality of the CNN established during training. The independent CNN regressors are designed to have different receptive fields and a switch classifier is trained to relay the crowd scene patch to the best CNN regressor. We perform extensive experiments on all major crowd counting datasets and evidence better performance compared to current state-of-the-art methods. We provide interpretable representations of the multichotomy of space of crowd scene patches inferred from the switch. It is observed that the switch relays an image patch to a particular CNN column based on density of crowd.	\N
a4c0f18b-853d-49ba-89c0-9cb4b6f490a6	Feature Mining for Localised Crowd Counting	2025-08-03 19:54:48.735733+00	2025-08-03 19:54:48.735733+00	\N	\N	\N	\N	\N	f	{"Ke Chen","Chen Change Loy","Shaogang Gong","Tony Xiang"}	{}	2025-08-03 19:54:48.735733+00	2025-08-03 19:54:48.735733+00	\N	\N	\N	https://doi.org/10.5244/c.26.21	This paper presents a multi-output regression model for crowd counting in public scenes. Existing counting by regression methods either learn a single model for global counting, or train a large number of separate regressors for localised density estimation. In contrast, our single regression model based approach is able to estimate people count in spatially localised regions and is more scalable without the need for training a large number of regressors proportional to the number of local regions. In particular, the proposed model automatically learns the functional mapping between interdependent low-level features and multi-dimensional structured outputs. The model is able to discover the inherent importance of different features for people counting at different spatial locations. Extensive evaluations on an existing crowd analysis benchmark dataset and a new more challenging dataset demonstrate the effectiveness of our approach.	\N
8795f4f7-7a94-4e3e-9128-2a23e1c7ee0c	Context-Aware Crowd Counting	2025-08-03 19:54:54.836291+00	2025-08-03 19:54:54.836291+00	papers/context-aware-crowd-counting-8795f4f7-7a94-4e3e-9128-2a23e1c7ee0c.pdf	\N	6532663	\N	ed223f687f1544224628739c09f000d3	f	{"Weizhe Liu","Mathieu Salzmann","Pascal Fua"}	{}	2025-08-03 19:54:54.836291+00	2025-08-03 19:54:54.867758+00	\N	\N	1811.10452v2	\N	State-of-the-art methods for counting people in crowded scenes rely on deep networks to estimate crowd density. They typically use the same filters over the whole image or over large image patches. Only then do they estimate local scale to compensate for perspective distortion. This is typically achieved by training an auxiliary classifier to select, for predefined image patches, the best kernel size among a limited set of choices. As such, these methods are not end-to-end trainable and restricted in the scope of context they can leverage. In this paper, we introduce an end-to-end trainable deep architecture that combines features obtained using multiple receptive field sizes and learns the importance of each such feature at each image location. In other words, our approach adaptively encodes the scale of the contextual information required to accurately predict crowd density. This yields an algorithm that outperforms state-of-the-art crowd counting methods, especially when perspective effects are strong.	\N
ccd831d1-af5f-4e13-9f84-d4fd72e4a453	Single-Image Crowd Counting via Multi-Column Convolutional Neural Network	2025-08-03 20:27:48.970525+00	2025-08-03 20:27:48.970525+00	\N	\N	\N	\N	\N	f	{"Yingying Zhang","Desen Zhou","Siqin Chen","Shenghua Gao","Yi Ma"}	{}	2025-08-03 20:27:48.970525+00	2025-08-03 20:27:48.970525+00	\N	\N	\N	https://doi.org/10.1109/cvpr.2016.70	This paper aims to develop a method than can accurately estimate the crowd count from an individual image with arbitrary crowd density and arbitrary perspective. To this end, we have proposed a simple but effective Multi-column Convolutional Neural Network (MCNN) architecture to map the image to its crowd density map. The proposed MCNN allows the input image to be of arbitrary size or resolution. By utilizing filters with receptive fields of different sizes, the features learned by each column CNN are adaptive to variations in people/head size due to perspective effect or image resolution. Furthermore, the true density map is computed accurately based on geometry-adaptive kernels which do not need knowing the perspective map of the input image. Since exiting crowd counting datasets do not adequately cover all the challenging situations considered in our work, we have collected and labelled a large new dataset that includes 1198 images with about 330,000 heads annotated. On this challenging new dataset, as well as all existing datasets, we conduct extensive experiments to verify the effectiveness of the proposed model and method. In particular, with the proposed simple MCNN model, our method outperforms all existing methods. In addition, experiments show that our model, once trained on one dataset, can be readily transferred to a new dataset.	\N
a904c145-e18c-4fb3-b9f3-b9088267a4d5	Cross-scene crowd counting via deep convolutional neural networks	2025-08-03 20:27:48.994253+00	2025-08-03 20:27:48.994253+00	\N	\N	\N	\N	\N	f	{"Cong Zhang","Hongsheng Li","Xiaogang Wang","Xiaokang Yang"}	{}	2025-08-03 20:27:48.994253+00	2025-08-03 20:27:48.994253+00	\N	\N	\N	https://doi.org/10.1109/cvpr.2015.7298684	Cross-scene crowd counting is a challenging task where no laborious data annotation is required for counting people in new target surveillance crowd scenes unseen in the training set. The performance of most existing crowd counting methods drops significantly when they are applied to an unseen scene. To address this problem, we propose a deep convolutional neural network (CNN) for crowd counting, and it is trained alternatively with two related learning objectives, crowd density and crowd count. This proposed switchable learning approach is able to obtain better local optimum for both objectives. To handle an unseen target crowd scene, we present a data-driven method to fine-tune the trained CNN model for the target scene. A new dataset including 108 crowd scenes with nearly 200,000 head annotations is introduced to better evaluate the accuracy of cross-scene crowd counting methods. Extensive experiments on the proposed and another two existing datasets demonstrate the effectiveness and reliability of our approach.	\N
9ac99dd4-8b35-4384-b64c-6c9fa1106a75	Switching Convolutional Neural Network for Crowd Counting	2025-08-03 20:27:49.006139+00	2025-08-03 20:27:49.006139+00	\N	\N	\N	\N	\N	f	{"Deepak Babu Sam","Shiv Surya","R. Venkatesh Babu"}	{}	2025-08-03 20:27:49.006139+00	2025-08-03 20:27:49.006139+00	\N	\N	\N	https://doi.org/10.1109/cvpr.2017.429	We propose a novel crowd counting model that maps a given crowd scene to its density. Crowd analysis is compounded by myriad of factors like inter-occlusion between people due to extreme crowding, high similarity of appearance between people and background elements, and large variability of camera view-points. Current state-of-the art approaches tackle these factors by using multi-scale CNN architectures, recurrent networks and late fusion of features from multi-column CNN with different receptive fields. We propose switching convolutional neural network that leverages variation of crowd density within an image to improve the accuracy and localization of the predicted crowd count. Patches from a grid within a crowd scene are relayed to independent CNN regressors based on crowd count prediction quality of the CNN established during training. The independent CNN regressors are designed to have different receptive fields and a switch classifier is trained to relay the crowd scene patch to the best CNN regressor. We perform extensive experiments on all major crowd counting datasets and evidence better performance compared to current state-of-the-art methods. We provide interpretable representations of the multichotomy of space of crowd scene patches inferred from the switch. It is observed that the switch relays an image patch to a particular CNN column based on density of crowd.	\N
3ae7e40f-11c2-4e2d-87f7-2baebf2dff3f	Feature Mining for Localised Crowd Counting	2025-08-03 20:27:49.01714+00	2025-08-03 20:27:49.01714+00	\N	\N	\N	\N	\N	f	{"Ke Chen","Chen Change Loy","Shaogang Gong","Tony Xiang"}	{}	2025-08-03 20:27:49.01714+00	2025-08-03 20:27:49.01714+00	\N	\N	\N	https://doi.org/10.5244/c.26.21	This paper presents a multi-output regression model for crowd counting in public scenes. Existing counting by regression methods either learn a single model for global counting, or train a large number of separate regressors for localised density estimation. In contrast, our single regression model based approach is able to estimate people count in spatially localised regions and is more scalable without the need for training a large number of regressors proportional to the number of local regions. In particular, the proposed model automatically learns the functional mapping between interdependent low-level features and multi-dimensional structured outputs. The model is able to discover the inherent importance of different features for people counting at different spatial locations. Extensive evaluations on an existing crowd analysis benchmark dataset and a new more challenging dataset demonstrate the effectiveness of our approach.	\N
916d8a22-654d-4386-8531-c09844810aca	Context-Aware Crowd Counting	2025-08-03 20:27:49.298438+00	2025-08-03 20:27:49.298438+00	papers/context-aware-crowd-counting-916d8a22-654d-4386-8531-c09844810aca.pdf	\N	6532663	\N	ed223f687f1544224628739c09f000d3	f	{"Weizhe Liu","Mathieu Salzmann","Pascal Fua"}	{}	2025-08-03 20:27:49.298438+00	2025-08-03 20:27:49.340871+00	\N	\N	1811.10452v2	\N	State-of-the-art methods for counting people in crowded scenes rely on deep networks to estimate crowd density. They typically use the same filters over the whole image or over large image patches. Only then do they estimate local scale to compensate for perspective distortion. This is typically achieved by training an auxiliary classifier to select, for predefined image patches, the best kernel size among a limited set of choices. As such, these methods are not end-to-end trainable and restricted in the scope of context they can leverage. In this paper, we introduce an end-to-end trainable deep architecture that combines features obtained using multiple receptive field sizes and learns the importance of each such feature at each image location. In other words, our approach adaptively encodes the scale of the contextual information required to accurately predict crowd density. This yields an algorithm that outperforms state-of-the-art crowd counting methods, especially when perspective effects are strong.	\N
b0f626fc-2961-4b91-a316-7593023569ef	Development and Validation of a Deep Learning System for Diabetic Retinopathy and Related Eye Diseases Using Retinal Images From Multiethnic Populations With Diabetes	2025-08-03 20:31:19.15418+00	2025-08-03 20:31:19.15418+00	\N	\N	\N	\N	\N	f	{"Daniel Shu Wei Ting","Carol Y. Cheung","Gilbert Lim","Gavin Siew Wei Tan","Duc Quang Nguyen","Alfred Tau Liang Gan","Haslina Hamzah","Renata García-Franco","Ian Yeo","Shu Yen Lee","Edmund Yick Mun Wong","Charumathi Sabanayagam","Mani Baskaran","Farah Ibrahim","Ngiap Chuan Tan","Eric Finkelstein","Ecosse L. Lamoureux","Yhi Wong","Neil M. Bressler","Sobha Sivaprasad","Rohit Varma","Jost B. Jonas","Mingguang He","Ching‐Yu Cheng","Chui Ming Gemmy Cheung","Tin Aung","Wynne Hsu","Mong Li Lee","Tien Yin Wong"}	{}	2025-08-03 20:31:19.15418+00	2025-08-03 20:31:19.15418+00	\N	\N	\N	https://doi.org/10.1001/jama.2017.18152	<h3>Importance</h3> A deep learning system (DLS) is a machine learning technology with potential for screening diabetic retinopathy and related eye diseases. <h3>Objective</h3> To evaluate the performance of a DLS in detecting referable diabetic retinopathy, vision-threatening diabetic retinopathy, possible glaucoma, and age-related macular degeneration (AMD) in community and clinic-based multiethnic populations with diabetes. <h3>Design, Setting, and Participants</h3> Diagnostic performance of a DLS for diabetic retinopathy and related eye diseases was evaluated using 494 661 retinal images. A DLS was trained for detecting diabetic retinopathy (using 76 370 images), possible glaucoma (125 189 images), and AMD (72 610 images), and performance of DLS was evaluated for detecting diabetic retinopathy (using 112 648 images), possible glaucoma (71 896 images), and AMD (35 948 images). Training of the DLS was completed in May 2016, and validation of the DLS was completed in May 2017 for detection of referable diabetic retinopathy (moderate nonproliferative diabetic retinopathy or worse) and vision-threatening diabetic retinopathy (severe nonproliferative diabetic retinopathy or worse) using a primary validation data set in the Singapore National Diabetic Retinopathy Screening Program and 10 multiethnic cohorts with diabetes. <h3>Exposures</h3> Use of a deep learning system. <h3>Main Outcomes and Measures</h3> Area under the receiver operating characteristic curve (AUC) and sensitivity and specificity of the DLS with professional graders (retinal specialists, general ophthalmologists, trained graders, or optometrists) as the reference standard. <h3>Results</h3> In the primary validation dataset (n = 14 880 patients; 71 896 images; mean [SD] age, 60.2 [2.2] years; 54.6% men), the prevalence of referable diabetic retinopathy was 3.0%; vision-threatening diabetic retinopathy, 0.6%; possible glaucoma, 0.1%; and AMD, 2.5%. The AUC of the DLS for referable diabetic retinopathy was 0.936 (95% CI, 0.925-0.943), sensitivity was 90.5% (95% CI, 87.3%-93.0%), and specificity was 91.6% (95% CI, 91.0%-92.2%). For vision-threatening diabetic retinopathy, AUC was 0.958 (95% CI, 0.956-0.961), sensitivity was 100% (95% CI, 94.1%-100.0%), and specificity was 91.1% (95% CI, 90.7%-91.4%). For possible glaucoma, AUC was 0.942 (95% CI, 0.929-0.954), sensitivity was 96.4% (95% CI, 81.7%-99.9%), and specificity was 87.2% (95% CI, 86.8%-87.5%). For AMD, AUC was 0.931 (95% CI, 0.928-0.935), sensitivity was 93.2% (95% CI, 91.1%-99.8%), and specificity was 88.7% (95% CI, 88.3%-89.0%). For referable diabetic retinopathy in the 10 additional datasets, AUC range was 0.889 to 0.983 (n = 40 752 images). <h3>Conclusions and Relevance</h3> In this evaluation of retinal images from multiethnic cohorts of patients with diabetes, the DLS had high sensitivity and specificity for identifying diabetic retinopathy and related eye diseases. Further research is necessary to evaluate the applicability of the DLS in health care settings and the utility of the DLS to improve vision outcomes.	\N
02f42c6b-b03c-444b-92eb-1d4b1d339d07	Diagnosis of Diabetic Eye Disease	2025-08-03 20:31:19.176528+00	2025-08-03 20:31:19.176528+00	\N	\N	\N	\N	\N	f	{"Elliot J. Sussman"}	{}	2025-08-03 20:31:19.176528+00	2025-08-03 20:31:19.176528+00	\N	\N	\N	https://doi.org/10.1001/jama.1982.03320480047025	The correct diagnosis of proliferation diabetic retinopathy is essential, because it is a treatable disease and missing the diagnosis can lead to the patient becoming blind. We examined the ability of internists and ophthalmologists to diagnose proliferative retinopathy under optimal conditions. Twenty-three physicians performed retinal examinations on ten diabetic patients and one normal patient with dilated pupils. Physician examiners were members of a university medical center and included 10 internists, 2 diabetologists, 4 senior medical residents, 4 general ophthalmologists, and 3 ophthalmologists who were subspecialists in retinal disease. Correct diagnosis was determined separately by the consensus of three ophthalmologists specializing in retinal disease, who reviewed seven-view stereo fundus photographs and medical charts. Of a possible 483 individual eye a examinations, 438 were completed. The overall error rate was 61%. The error rate for missing the diagnosis of proliferative retinopathy varied from 0% for retinal specialists to 49% for internists, diabetologists, and medical residents. We conclude that potentially serious mistakes in diagnosis are currently made by the physicians who care for most diabetic patients. Experience and specialized knowledge lessen that the error rate. Further education or greater use of referrals may be necessary to provide optimal patient care.	\N
e16ecd63-1357-4c6c-9ebd-15044bdddbb3	Cost effectiveness analysis of screening for sight threatening diabetic eye disease	2025-08-03 20:31:19.186246+00	2025-08-03 20:31:19.186246+00	\N	\N	\N	\N	\N	f	{"Mark A. James"}	{}	2025-08-03 20:31:19.186246+00	2025-08-03 20:31:19.186246+00	\N	\N	\N	https://doi.org/10.1136/bmj.320.7250.1627	<h3>Abstract</h3> <b>Objective:</b> To measure the cost effectiveness of systematic photographic screening for sight threatening diabetic eye disease compared with existing practice. <b>Design:</b> Cost effectiveness analysis <b>Setting:</b> Liverpool. <b>Subjects:</b> A target population of 5000 diabetic patients invited for screening. <b>Main outcome measures:</b> Cost effectiveness (cost per true positive) of systematic and opportunistic programmes; incremental cost effectiveness of replacing opportunistic with systematic screening. <b>Results:</b> Baseline prevalence of sight threatening eye disease was 14.1%. The cost effectiveness of the systematic programme was £209 (sensitivity 89%, specificity 86%, compliance 80%, annual cost £104 996) and of the opportunistic programme was £289 (combined sensitivity 63%, specificity 92%, compliance 78%, annual cost £99 981). The incremental cost effectiveness of completely replacing the opportunistic programme was £32. Absolute values of cost effectiveness were highly sensitive to varying prevalence, sensitivity and specificity, compliance, and programme size. <b>Conclusion:</b> Replacing existing programmes with systematic screening for diabetic eye disease is justified.	\N
e44ac4b7-7238-4dbe-9424-412c3647edae	Effect of mydriasis and different field strategies on digital image screening of diabetic eye disease	2025-08-03 20:31:19.195912+00	2025-08-03 20:31:19.195912+00	\N	\N	\N	\N	\N	f	{"Helen Murgatroyd"}	{}	2025-08-03 20:31:19.195912+00	2025-08-03 20:31:19.195912+00	\N	\N	\N	https://doi.org/10.1136/bjo.2003.026385	<b>Aims:</b> To assess the effects of (1) mydriasis and (2) single versus three field photography on screening for diabetic eye disease using digital photography <b>Method:</b> Slit lamp examination findings were compared to digital fundal photographs for the detection of any retinopathy and for referable retinopathy in 398 patients (794 eyes). A Topcon TRC-NW6S digital non-mydriatic fundus camera was used. Three photographic strategies were used: undilated single field, dilated single field, and dilated multiple fields. The photographs were presented in random order to one of two retinal screeners. For the single field photographs the screeners were masked to the use of mydriatics. In 13% of fundal photographs, grading was performed by both, rather than just one grader. <b>Results:</b> Mydriasis reduced the proportion of ungradable photographs from 26% to 5% (p&lt;0.001). Neither mydriasis nor three field photography improved the sensitivity or specificity for the detection of any retinopathy or of referable retinopathy when compared with undilated single field photography. The sensitivity and specificity for detecting referable retinopathy using undilated single field photography was 77% (95% CI 71 to 84) and 95 % (95% CI 93 to 97) respectively. Using dilated single field photography the figures were 81% (95% CI 76 to 87) and 92% (95% CI 90 to 94) respectively. Using dilated three field photography the figures were 83% (95% CI 78 to 88) and 93% (95% CI 91 to 96) respectively. Intergrader reliability for the detection of referable retinopathy in gradable photographs was excellent (Kappa values 0.86–1.00). <b>Conclusions:</b> Mydriasis reduces the technical failure rate. Mydriasis and the three field photography as used in this study do not increase the sensitivity or specificity of detecting diabetic retinopathy.	\N
612740c9-e944-42fa-bdeb-b0c27c39a4cd	The role of inflammation in diabetic eye disease	2025-08-03 20:31:19.205182+00	2025-08-03 20:31:19.205182+00	\N	\N	\N	\N	\N	f	{"Marina Mesquida","Faye Drawnel","Sascha Fauser"}	{}	2025-08-03 20:31:19.205182+00	2025-08-03 20:31:19.205182+00	\N	\N	\N	https://doi.org/10.1007/s00281-019-00750-7		\N
00b2848f-d0b0-4623-a321-bc74539f9703	Attention Is All You Need	2025-08-03 20:42:51.525921+00	2025-08-03 20:42:51.525921+00	papers/170603762v7pdf-00b2848f-d0b0-4623-a321-bc74539f9703.pdf	\N	2215244	application/pdf	18e1b007a1dab45b30cc861ba2dfda25	t	{"Ashish Vaswani","Noam Shazeer","Google Brain","Niki Parmar","Jakob Uszkoreit","Llion Jones","Aidan Gomez","Łukasz Kaiser","Google Research","University of Toronto","31st Conference on Neural Information Processing Systems (NIPS 2017) \n\t\t\t\t\t\t\t\t \n\t\t\t\t\t\t\t\t\t Long Beach \n\t\t\t\t\t\t\t\t\t CA \n\t\t\t\t\t\t\t\t\t USA"}	{}	2025-08-03 20:42:51.525921+00	2025-08-03 20:42:51.57526+00	\N	xml/00b2848f-d0b0-4623-a321-bc74539f9703.xml	\N	\N	The dominant sequence transduction models are based on complex recurrent or convolutional neural networks that include an encoder and a decoder. The best performing models also connect the encoder and decoder through an attention mechanism. We propose a new simple network architecture, the Transformer, based solely on attention mechanisms, dispensing with recurrence and convolutions entirely. Experiments on two machine translation tasks show these models to be superior in quality while being more parallelizable and requiring significantly less time to train. Our model achieves 28.4 BLEU on the WMT 2014 Englishto-German translation task, improving over the existing best results, including ensembles, by over 2 BLEU. On the WMT 2014 English-to-French translation task, our model establishes a new single-model state-of-the-art BLEU score of 41.8 after training for 3.5 days on eight GPUs, a small fraction of the training costs of the best models from the literature. We show that the Transformer generalizes well to other tasks by applying it successfully to English constituency parsing both with large and limited training data. * Equal contribution. Listing order is random. Jakob proposed replacing RNNs with self-attention and started the effort to evaluate this idea. Ashish, with Illia, designed and implemented the first Transformer models and has been crucially involved in every aspect of this work. Noam proposed scaled dot-product attention, multi-head attention and the parameter-free position representation and became the other person involved in nearly every detail. Niki designed, implemented, tuned and evaluated countless model variants in our original codebase and tensor2tensor. Llion also experimented with novel model variants, was responsible for our initial codebase, and efficient inference and visualizations. Lukasz and Aidan spent countless long days designing various parts of and implementing tensor2tensor, replacing our earlier codebase, greatly improving results and massively accelerating our research. † Work performed while at Google Brain. ‡ Work performed while at Google Research.	attention-is-all-you-need
a6df804b-9eae-4e20-9dcd-f730c04d6058	FGA: Fourier-Guided Attention Network for Crowd Count Estimation	2025-08-03 20:43:20.706106+00	2025-08-03 20:43:20.706106+00	papers/240706110v1pdf-a6df804b-9eae-4e20-9dcd-f730c04d6058.pdf	\N	11356498	application/pdf	ded02c46ba558a587822c1c6a47133a3	t	{"Yashwardhan Chaudhuri","Ankit Kumar","Arun Buduru","Adel Alshamrani"}	{"Crowd Count Estimation","Fast Fourier Transformation",Attention,"Channel Attention","Spatial Attention",CNN}	2025-08-03 20:43:20.706106+00	2025-08-03 20:43:20.801036+00	\N	xml/a6df804b-9eae-4e20-9dcd-f730c04d6058.xml	\N	\N	Crowd counting is gaining societal relevance, particularly in domains of Urban Planning, Crowd Management, and Public Safety. This paper introduces Fourier-guided attention (FGA), a novel attention mechanism for crowd count estimation designed to address the inefficient full-scale global pattern capture in existing works on convolutionbased attention networks. FGA efficiently captures multi-scale information, including full-scale global patterns, by utilizing Fast-Fourier Transformations (FFT) along with spatial attention for global features and convolutions with channel-wise attention for semi-global and local features. The architecture of FGA involves a dual-path approach: (1) a path for processing full-scale global features through FFT, allowing for efficient extraction of information in the frequency domain, and (2) a path for processing remaining feature maps for semi-global and local features using traditional convolutions and channelwise attention. This dual-path architecture enables FGA to seamlessly integrate frequency and spatial information, enhancing its ability to capture diverse crowd patterns. We apply FGA in the last layers of two popular crowd-counting works, CSRNet and CANNet, to evaluate the module's performance on benchmark datasets such as ShanghaiTech-A, ShanghaiTech-B, UCF-CC-50, and JHU++ crowd. The experiments demonstrate a notable improvement across all datasets based on Mean-Squared-Error (MSE) and Mean-Absolute-Error (MAE) metrics, showing comparable performance to recent state-of-the-art methods. Additionally, we illustrate the interpretability using qualitative analysis, leveraging Grad-CAM heatmaps, to show the effectiveness of FGA in capturing crowd patterns.	fga-fourier-guided-attention-network-for-crowd-count-estimation
23a1834f-a5b2-469c-a0f2-3658136a9344	Lecture Notes_ Neural Network Architectures.pdf	2025-08-03 20:44:05.714775+00	2025-08-03 20:44:05.714775+00	papers/lecture-notes_-neural-network-architecturespdf-23a1834f-a5b2-469c-a0f2-3658136a9344.pdf	\N	6857612	application/pdf	232c2c76e7cada2373394c1c585c22c9	t	{"H Antil","T S Brown","R Löhner","F Togashi","D Verma","H Díaz","E Herberg","R Khatri","A Baldominos","Y Saez","P Isasi","Y Bengio","P Simard","P Frasconi","S Boyd","L Vandenberghe","R T Q Chen","Y Rubanova","J Bettencourt","D K Duvenaud"}	{}	2025-08-03 20:44:05.714775+00	2025-08-03 20:44:05.774498+00	\N	xml/23a1834f-a5b2-469c-a0f2-3658136a9344.xml	\N	\N	\N	\N
6300b3d8-1cdc-4a76-a5a9-4eaae00352e7	C-lisp and Flexible Macro Programming with S-expressions	2025-08-03 20:43:42.9075+00	2025-08-03 20:43:42.9075+00	papers/241016690v2pdf-6300b3d8-1cdc-4a76-a5a9-4eaae00352e7.pdf	\N	94664	application/pdf	baf2174bd0b4e608aebce57cce917925	t	{"Vedanth Padmaraman","Sasank Chilamkurthy"}	{}	2025-08-03 20:43:42.9075+00	2025-08-03 20:43:42.931371+00	\N	xml/6300b3d8-1cdc-4a76-a5a9-4eaae00352e7.xml	\N	\N	Llama.lisp is a compiler framework intended to target offload processor backends such as GPUs, using intermediate representation languages (IRs) that are device-agnostic. The Llama.lisp IRs are formulated as S-expressions. This makes them easy to generate using higher level programming languages, which is one of the primary goals for Llama.lisp. The highest IR layer currently implemented in Llama.lisp is C-Lisp. In this paper, we describe the macro system developed for the Llama.lisp compiler framework. We show how we implemented FFI bindings as an example of this system. Compilers are workhorses of performance behind all AI algorithms. Making algorithms work effectively on GPUs is especially hard -called kernel programming. The compiler ecosystem around GPUs is especially fragmented. They are supposed to allow for performance portability between different hardware architecture. Unfortunately, this is usually not the case. We are designing a compiler framework called llama.lisp [1] to solve this problem. As suggested by the name, the framework is highly inspired by Lisp and its syntax, S-expressions. A multi layered approach is adopted to tame the complexity of writing such a compiler framework. We implement C-lisp as one such layer. We show how lisp syntax has allowed for unique meta programming capabilities while being simple both to understand and implement.	c-lisp-and-flexible-macro-programming-with-s-expressions
c32bdae7-2c1e-4987-9d3d-da9244c3ce68	Machine Learning-driven Analysis of Gastrointestinal Symptoms in Post-COVID-19 Patients	2025-08-03 20:44:34.902459+00	2025-08-03 20:44:34.902459+00	papers/machine-learning-driven-analysis-of-gastrointestinal-symptoms-in-post-covid-19-patientspdf-c32bdae7-2c1e-4987-9d3d-da9244c3ce68.pdf	\N	327398	application/pdf	527a718fd7851501b348f756733d0b6a	t	{"Maitham Yousif","Fadhil Al-Amran","Salman Rawaf","Mohammad Grmt","Maithm Ghaly"}	{COVID-19,"gastrointestinal symptoms","machine learning","predictive factors","post-COVID-19 care","long COVID"}	2025-08-03 20:44:34.902459+00	2025-08-03 20:44:34.928599+00	\N	xml/c32bdae7-2c1e-4987-9d3d-da9244c3ce68.xml	\N	\N	The COVID-19 pandemic, caused by the novel coronavirus SARS-CoV-2, has posed significant health challenges worldwide. While respiratory symptoms have been the primary focus, emerging evidence has highlighted the impact of COVID-19 on various organ systems, including the gastrointestinal (GI) tract. This study, based on data from 913 post-COVID-19 patients in Iraq collected during 2022 and 2023, investigates the prevalence and patterns of GI symptoms in individuals recovering from COVID-19 and leverages machine learning algorithms to identify predictive factors for these symptoms. The research findings reveal that a notable percentage of post-COVID-19 patients experience GI symptoms during their recovery phase. Diarrhea emerged as the most frequently reported symptom, followed by abdominal pain and nausea. Machine learning analysis uncovered significant predictive factors for GI symptoms, including age, gender, disease severity, comorbidities, and the duration of COVID-19 illness. These findings underscore the importance of monitoring and addressing GI symptoms in post-COVID-19 care, with machine learning offering valuable tools for early identification and personalized intervention. This study contributes to the understanding of the longterm consequences of COVID-19 on GI health and emphasizes the potential benefits of utilizing machine learning-driven analysis in predicting and managing these symptoms. Further research is warranted to delve into the mechanisms underlying GI symptoms in COVID-19 survivors and to develop targeted interventions for symptom management.	machine-learning-driven-analysis-of-gastrointestinal-symptoms-in-post-covid-19-patients
bb06552e-636d-4237-807e-2cc4c73338f4	2302.05374v1.pdf	2025-08-03 21:41:59.79203+00	2025-08-03 21:41:59.79203+00	papers/230205374v1pdf-bb06552e-636d-4237-807e-2cc4c73338f4.pdf	\N	5948085	application/pdf	14589224d0f85d97b10c0978b8885c06	t	{}	{}	2025-08-03 21:41:59.79203+00	2025-08-03 22:00:04.7271+00	\N	\N	\N	\N	\N	\N
f9c43b41-6e01-4571-ae88-909821c25fed	CSRNet: Dilated Convolutional Neural Networks for Understanding the Highly Congested Scenes	2025-08-03 22:03:14.876021+00	2025-08-03 22:03:14.876021+00	papers/180210062pdf-f9c43b41-6e01-4571-ae88-909821c25fed.pdf	bib/f9c43b41-6e01-4571-ae88-909821c25fed.bib	9144250	application/pdf	068ef379e36f35e32e7d679d8bc889dc	t	{"Yuhong Li","Xiaofan Zhang","Deming Chen"}	{}	2025-08-03 22:03:14.876021+00	2025-08-03 22:03:14.967012+00	\N	xml/f9c43b41-6e01-4571-ae88-909821c25fed.xml	\N	\N	We propose a network for Congested Scene Recognition called CSRNet to provide a data-driven and deep learning method that can understand highly congested scenes and perform accurate count estimation as well as present highquality density maps. The proposed CSRNet is composed of two major components: a convolutional neural network (CNN) as the front-end for 2D feature extraction and a dilated CNN for the back-end, which uses dilated kernels to deliver larger reception fields and to replace pooling operations. CSRNet is an easy-trained model because of its pure convolutional structure. We demonstrate CSRNet on four datasets (ShanghaiTech dataset, the UCF CC 50 dataset, the WorldEXPO'10 dataset, and the UCSD dataset) and we deliver the state-of-the-art performance. In the Shang-haiTech Part B dataset, CSRNet achieves 47.3% lower Mean Absolute Error (MAE) than the previous state-of-theart method. We extend the targeted applications for counting other objects, such as the vehicle in TRANCOS dataset. Results show that CSRNet significantly improves the output quality with 15.4% lower MAE than the previous state-ofthe-art approach.	csrnet-dilated-convolutional-neural-networks-for-understanding-the-highly-congested-scenes
d28b3211-9f93-4271-8d5b-680807b486e0	Diabetic Retinopathy Detection using Ensemble Machine Learning	2025-08-03 22:04:32.718726+00	2025-08-03 22:04:32.718726+00	papers/210612545v1pdf-d28b3211-9f93-4271-8d5b-680807b486e0.pdf	bib/d28b3211-9f93-4271-8d5b-680807b486e0.bib	1348767	application/pdf	74a95710fd125eb2be2819f5fb78e327	t	{"Israa Odeh","Mouhammd Alkasassbeh","Mohammad Alauthman"}	{"Diabetic Retinopathy","Ensemble learning","Machine learning"}	2025-08-03 22:04:32.718726+00	2025-08-03 22:04:32.74827+00	\N	xml/d28b3211-9f93-4271-8d5b-680807b486e0.xml	\N	\N	Diabetic Retinopathy (DR) is among the world's leading vision loss causes in diabetic patients. DR is a microvascular disease that affects the eye retina, which causes vessel blockage and therefore cuts the main source of nutrition for the retina tissues. Treatment for this visual disorder is most effective when it is detected in its earliest stages, as severe DR can result in irreversible blindness. Nonetheless, DR identification requires the expertise of Ophthalmologists which is often expensive and time-consuming. Therefore, automatic detection systems were introduced aiming to facilitate the identification process, making it available globally in a time and cost-efficient manner. However, due to the limited reliable datasets and medical records for this particular eye disease, the obtained predictions' accuracies were relatively unsatisfying for eye specialists to rely on them as diagnostic systems. Thus, we explored an ensemble-based learning strategy, merging a substantial selection of well-known classification algorithms in one sophisticated diagnostic model. The proposed framework achieved the highest accuracy rates among all other common classification algorithms in the area. 4 subdatasets were generated to contain the top 5 and top 10 features of the Messidor dataset, selected by InfoGainEval. and WrapperSubsetEval., accuracies of 70.7% and 75.1% were achieved on the InfoGainEval. top 5 and original dataset respectively. The results imply the impressive performance of the subdataset, which significantly conduces to a less complex classification process when compared to the original complete Messidor dataset.	diabetic-retinopathy-detection-using-ensemble-machine-learning
3d228d2f-6e0b-438f-828a-432e7e8b7247	AUTOMATED SMARTPHONE BASED SYSTEM FOR DIAGNOSIS OF DIABETIC RETINOPATHY	2025-08-03 22:03:41.38287+00	2025-08-03 22:03:41.38287+00	papers/200403408v1pdf-3d228d2f-6e0b-438f-828a-432e7e8b7247.pdf	bib/3d228d2f-6e0b-438f-828a-432e7e8b7247.bib	552043	application/pdf	19850897270a7e79b1cd592b2453c05f	t	{"Misgina Hagos","Shri Kant","Surayya Ado Bala"}	{}	2025-08-03 22:03:41.38287+00	2025-08-03 22:03:41.411456+00	\N	xml/3d228d2f-6e0b-438f-828a-432e7e8b7247.xml	\N	\N	Early diagnosis of diabetic retinopathy for treatment of the disease has been failing to reach diabetic people living in rural areas. Shortage of trained ophthalmologists, limited availability of healthcare centers, and expensiveness of diagnostic equipment are among the reasons. Although many deep learning-based automatic diagnosis of diabetic retinopathy techniques have been implemented in the literature, these methods still fail to provide a point-of-care diagnosis. This raises the need for an independent diagnostic of diabetic retinopathy that can be used by a non-expert. Recently the usage of smartphones has been increasing across the world. Automated diagnoses of diabetic retinopathy can be deployed on smartphones in order to provide an instant diagnosis to diabetic people residing in remote areas. In this paper, inception based convolutional neural network and binary decision tree-based ensemble of classifiers have been proposed and implemented to detect and classify diabetic retinopathy. The proposed method was further imported into a smartphone application for mobile-based classification, which provides an offline and automatic system for diagnosis of diabetic retinopathy.	automated-smartphone-based-system-for-diagnosis-of-diabetic-retinopathy
135598cf-16f6-46c7-948a-db8275485a68	Automated Diabetic Retinopathy Grading using Deep Convolutional Neural Network	2025-08-03 22:04:04.858776+00	2025-08-03 22:04:04.858776+00	papers/200406334v1pdf-135598cf-16f6-46c7-948a-db8275485a68.pdf	bib/135598cf-16f6-46c7-948a-db8275485a68.bib	2066818	application/pdf	6b05787c6047ed7c8b505517483643d1	t	{"Saket Chaturvedi","Kajol Gupta","Vaishali Ninawe","Prakash Prasad"}	{"Deep Learning","Diabetic Retinopathy","DenseNet network","Fundus Photography","Computeraided diagnosis"}	2025-08-03 22:04:04.858776+00	2025-08-03 22:04:04.895864+00	\N	xml/135598cf-16f6-46c7-948a-db8275485a68.xml	\N	\N	Diabetic Retinopathy is a global health problem, influences 100 million individuals worldwide, and in the next few decades, these incidences are expected to reach epidemic proportions. Diabetic Retinopathy is a subtle eye disease that can cause sudden, irreversible vision loss. The early-stage Diabetic Retinopathy diagnosis can be challenging for human experts, considering the visual complexity of fundus photography retinal images. However, Early Stage detection of Diabetic Retinopathy can significantly alter the severe vision loss problem. The competence of computer-aided detection systems to accurately detect the Diabetic Retinopathy had popularized them among researchers. In this study, we have utilized a pre-trained DenseNet121 network with several modifications and trained on APTOS 2019 dataset. The proposed method outperformed other stateof-the-art networks in early-stage detection and achieved 96.51% accuracy in severity grading of Diabetic Retinopathy for multi-label classification and achieved 94.44% accuracy for single-class classification method. Moreover, the precision, recall, f1-score, and quadratic weighted kappa for our network was reported as 86%, 87%, 86%, and 91.96%, respectively. Our proposed architecture is simultaneously very simple, accurate, and efficient concerning computational time and space.	automated-diabetic-retinopathy-grading-using-deep-convolutional-neural-network
b3251a67-101b-40ab-a1e7-551c18ccbecb	DISTRIBUTIONAL SHIFTS IN AUTOMATED DIABETIC RETINOPATHY SCREENING	2025-08-03 21:59:20.751396+00	2025-08-03 21:59:20.751396+00	papers/210711822v1pdf-b3251a67-101b-40ab-a1e7-551c18ccbecb.pdf	bib/b3251a67-101b-40ab-a1e7-551c18ccbecb.bib	1390856	application/pdf	2d81c3f6b330c0d52c639f3006f09aba	t	{"Jay Nandy","Wynne Hsu","Mong Lee"}	{"Distributional Shift","Dirichlet Prior Network","Diabetic Retinopathy Screening",Out-of-distribution}	2025-08-03 21:59:20.751396+00	2025-08-03 22:05:00.532262+00	\N	xml/b3251a67-101b-40ab-a1e7-551c18ccbecb.xml	\N	\N	Deep learning-based models are developed to automatically detect if a retina image is 'referable' in diabetic retinopathy (DR) screening. However, their classification accuracy degrades as the input images distributionally shift from their training distribution. Further, even if the input is not a retina image, a standard DR classifier produces a high confident prediction that the image is 'referable'. Our paper presents a Dirichlet Prior Network-based framework to address this issue. It utilizes an out-of-distribution (OOD) detector model and a DR classification model to improve generalizability by identifying OOD images. Experiments on real-world datasets indicate that the proposed framework can eliminate the unknown non-retina images and identify the distributionally shifted retina images for human intervention.	distributional-shifts-in-automated-diabetic-retinopathy-screening
\.


--
-- Data for Name: password_reset_tokens; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.password_reset_tokens (id, user_id, token, expires_at, used, created_at) FROM stdin;
\.


--
-- Data for Name: performance_metrics; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.performance_metrics (id, metric_name, metric_category, value, unit, metadata, recorded_at) FROM stdin;
\.


--
-- Data for Name: project_collaborators; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.project_collaborators (project_id, user_id, permission, added_at) FROM stdin;
\.


--
-- Data for Name: project_invitations; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.project_invitations (id, project_id, invited_by, email, role, permission, invitation_token, message, expires_at, accepted_at, accepted_by, declined_at, cancelled_at, cancelled_by, created_at) FROM stdin;
\.


--
-- Data for Name: project_members; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.project_members (id, user_id, project_id, role, added_at) FROM stdin;
aaeeb698-0666-47f5-999f-6ec407a79ff6	ff40fb7e-b5b8-436a-b16f-cc4a31146ff5	36eae63b-2fc6-4543-acab-2197c8a3cff6	owner	2025-08-03 19:49:53.96827+00
8840ca4f-c94a-40ea-8348-d5cc19a16d58	ff40fb7e-b5b8-436a-b16f-cc4a31146ff5	28f846fd-e8f5-48dd-814e-526854578e3a	owner	2025-08-03 20:24:04.635136+00
87f0a97a-ea7d-4014-a955-2bd233bf359c	ff40fb7e-b5b8-436a-b16f-cc4a31146ff5	7b2f8acd-a112-45f7-b166-3ba25f95e669	owner	2025-08-03 20:39:01.347069+00
\.


--
-- Data for Name: project_papers; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.project_papers (project_id, paper_id, uploaded, added_at) FROM stdin;
36eae63b-2fc6-4543-acab-2197c8a3cff6	77ec8d85-6e43-4254-aa0e-038b3a585cca	t	2025-08-03 19:53:00.52139+00
36eae63b-2fc6-4543-acab-2197c8a3cff6	4b830fca-7ca6-44fb-81f2-a1326837d41c	t	2025-08-03 19:54:48.693937+00
36eae63b-2fc6-4543-acab-2197c8a3cff6	26c4412b-a75a-4852-8b1d-b5164e7059a5	t	2025-08-03 19:54:48.705168+00
36eae63b-2fc6-4543-acab-2197c8a3cff6	a17ce92c-7a86-4b7b-9ec3-faa420c1ec69	t	2025-08-03 19:54:48.725861+00
36eae63b-2fc6-4543-acab-2197c8a3cff6	a4c0f18b-853d-49ba-89c0-9cb4b6f490a6	t	2025-08-03 19:54:48.735733+00
36eae63b-2fc6-4543-acab-2197c8a3cff6	8795f4f7-7a94-4e3e-9128-2a23e1c7ee0c	t	2025-08-03 19:54:54.836291+00
28f846fd-e8f5-48dd-814e-526854578e3a	ccd831d1-af5f-4e13-9f84-d4fd72e4a453	t	2025-08-03 20:27:48.970525+00
28f846fd-e8f5-48dd-814e-526854578e3a	a904c145-e18c-4fb3-b9f3-b9088267a4d5	t	2025-08-03 20:27:48.994253+00
28f846fd-e8f5-48dd-814e-526854578e3a	9ac99dd4-8b35-4384-b64c-6c9fa1106a75	t	2025-08-03 20:27:49.006139+00
28f846fd-e8f5-48dd-814e-526854578e3a	3ae7e40f-11c2-4e2d-87f7-2baebf2dff3f	t	2025-08-03 20:27:49.01714+00
28f846fd-e8f5-48dd-814e-526854578e3a	916d8a22-654d-4386-8531-c09844810aca	t	2025-08-03 20:27:49.298438+00
28f846fd-e8f5-48dd-814e-526854578e3a	b0f626fc-2961-4b91-a316-7593023569ef	t	2025-08-03 20:31:19.15418+00
28f846fd-e8f5-48dd-814e-526854578e3a	02f42c6b-b03c-444b-92eb-1d4b1d339d07	t	2025-08-03 20:31:19.176528+00
28f846fd-e8f5-48dd-814e-526854578e3a	e16ecd63-1357-4c6c-9ebd-15044bdddbb3	t	2025-08-03 20:31:19.186246+00
28f846fd-e8f5-48dd-814e-526854578e3a	e44ac4b7-7238-4dbe-9424-412c3647edae	t	2025-08-03 20:31:19.195912+00
28f846fd-e8f5-48dd-814e-526854578e3a	612740c9-e944-42fa-bdeb-b0c27c39a4cd	t	2025-08-03 20:31:19.205182+00
7b2f8acd-a112-45f7-b166-3ba25f95e669	00b2848f-d0b0-4623-a321-bc74539f9703	t	2025-08-03 20:42:51.525921+00
7b2f8acd-a112-45f7-b166-3ba25f95e669	a6df804b-9eae-4e20-9dcd-f730c04d6058	t	2025-08-03 20:43:20.706106+00
7b2f8acd-a112-45f7-b166-3ba25f95e669	6300b3d8-1cdc-4a76-a5a9-4eaae00352e7	t	2025-08-03 20:43:42.9075+00
7b2f8acd-a112-45f7-b166-3ba25f95e669	23a1834f-a5b2-469c-a0f2-3658136a9344	t	2025-08-03 20:44:05.714775+00
7b2f8acd-a112-45f7-b166-3ba25f95e669	c32bdae7-2c1e-4987-9d3d-da9244c3ce68	t	2025-08-03 20:44:34.902459+00
7b2f8acd-a112-45f7-b166-3ba25f95e669	bb06552e-636d-4237-807e-2cc4c73338f4	t	2025-08-03 21:41:59.79203+00
7b2f8acd-a112-45f7-b166-3ba25f95e669	b3251a67-101b-40ab-a1e7-551c18ccbecb	t	2025-08-03 21:59:20.751396+00
7b2f8acd-a112-45f7-b166-3ba25f95e669	f9c43b41-6e01-4571-ae88-909821c25fed	t	2025-08-03 22:03:14.876021+00
7b2f8acd-a112-45f7-b166-3ba25f95e669	3d228d2f-6e0b-438f-828a-432e7e8b7247	t	2025-08-03 22:03:41.38287+00
7b2f8acd-a112-45f7-b166-3ba25f95e669	135598cf-16f6-46c7-948a-db8275485a68	t	2025-08-03 22:04:04.858776+00
7b2f8acd-a112-45f7-b166-3ba25f95e669	d28b3211-9f93-4271-8d5b-680807b486e0	t	2025-08-03 22:04:32.718726+00
\.


--
-- Data for Name: projects; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.projects (id, name, slug, description, conversation_id, repo_url, created_by, created_at, updated_at, deleted_at, access_model) FROM stdin;
36eae63b-2fc6-4543-acab-2197c8a3cff6	Test-run	test-run	Project for investors to see initial run	\N	\N	ff40fb7e-b5b8-436a-b16f-cc4a31146ff5	2025-08-03 19:49:53.96827+00	2025-08-03 19:57:07.870824+00	2025-08-03 19:57:07.876082+00	role_based
28f846fd-e8f5-48dd-814e-526854578e3a	test-run	test-run	Something for our buddies to see	\N	\N	ff40fb7e-b5b8-436a-b16f-cc4a31146ff5	2025-08-03 20:24:04.635136+00	2025-08-03 20:38:45.508018+00	2025-08-03 20:38:45.527388+00	role_based
7b2f8acd-a112-45f7-b166-3ba25f95e669	Test-run	test-run	Something for our buddies to see	\N	\N	ff40fb7e-b5b8-436a-b16f-cc4a31146ff5	2025-08-03 20:39:01.347069+00	2025-08-03 20:39:01.347069+00	\N	role_based
\.


--
-- Data for Name: system_settings; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.system_settings (key, value, description, updated_at, updated_by) FROM stdin;
\.


--
-- Data for Name: task_activity; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.task_activity (id, task_id, user_id, action, field_changed, old_value, new_value, created_at) FROM stdin;
\.


--
-- Data for Name: task_assignees; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.task_assignees (task_id, user_id, assigned_by, assigned_at) FROM stdin;
\.


--
-- Data for Name: task_attachments; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.task_attachments (id, task_id, file_id, paper_id, attached_by, attached_at) FROM stdin;
\.


--
-- Data for Name: task_comments; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.task_comments (id, task_id, user_id, content, reply_to, created_at, updated_at, deleted_at) FROM stdin;
\.


--
-- Data for Name: task_dependencies; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.task_dependencies (id, predecessor_task_id, successor_task_id, dependency_type, created_at) FROM stdin;
\.


--
-- Data for Name: task_lists; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.task_lists (id, project_id, name, description, color, "position", created_by, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: task_recurrence; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.task_recurrence (id, task_id, recurrence_type, recurrence_interval, days_of_week, day_of_month, end_date, max_occurrences, created_at) FROM stdin;
\.


--
-- Data for Name: task_tags; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.task_tags (task_id, tag_id, user_id, tagged_at) FROM stdin;
\.


--
-- Data for Name: task_time_logs; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.task_time_logs (id, task_id, user_id, description, hours, log_date, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: task_watchers; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.task_watchers (task_id, user_id, watched_at) FROM stdin;
\.


--
-- Data for Name: tasks; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.tasks (id, project_id, task_list_id, parent_task_id, title, description, status, priority, due_date, start_date, estimated_hours, actual_hours, progress, created_by, assigned_to, "position", is_milestone, created_at, updated_at, completed_at, deleted_at) FROM stdin;
\.


--
-- Data for Name: user_behavior_patterns; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.user_behavior_patterns (id, user_id, pattern_type, pattern_data, confidence_score, last_updated, created_at) FROM stdin;
\.


--
-- Data for Name: user_engagement_daily; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.user_engagement_daily (id, user_id, date, total_sessions, total_time_minutes, features_used, papers_interacted, highlights_created, notes_created, chat_messages_sent, ai_interactions, latex_commits, login_count, created_at) FROM stdin;
\.


--
-- Data for Name: user_feature_usage; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.user_feature_usage (id, user_id, feature_name, feature_category, session_id, metadata, duration_seconds, success, created_at) FROM stdin;
\.


--
-- Data for Name: user_paper_tags; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.user_paper_tags (user_id, paper_id, tag_id, tagged_at) FROM stdin;
\.


--
-- Data for Name: user_project_tags; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.user_project_tags (user_id, project_id, tag_id, tagged_at) FROM stdin;
\.


--
-- Data for Name: user_saved_searches; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.user_saved_searches (id, user_id, name, search_query, filters, is_private, search_count, last_used_at, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: user_sessions; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.user_sessions (id, user_id, token_hash, expires_at, created_at, last_used_at, user_agent, ip_address) FROM stdin;
57127f59-cdeb-4294-af36-2d5f9821a0da	ff40fb7e-b5b8-436a-b16f-cc4a31146ff5	fce7d237edf6c6ae3fad6164c2dcb922c743db0998cfbad97c3b1709b2542391	2025-08-10 19:41:29.281371+00	2025-08-03 19:41:28.970035+00	2025-08-03 19:41:28.970035+00	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36	127.0.0.1
6faa814d-9c2d-4eb8-ada1-600c64f1948e	ff40fb7e-b5b8-436a-b16f-cc4a31146ff5	4a9f0d29c0f698131fcca59bacba9616672eec4c44a85c5c3b2f21515aca34a2	2025-08-10 19:41:53.694658+00	2025-08-03 19:41:53.403777+00	2025-08-03 19:41:53.403777+00	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36	127.0.0.1
cd3a6e86-f809-424b-b5ac-5f25b6c9fdcb	ff40fb7e-b5b8-436a-b16f-cc4a31146ff5	b2788db0fc8ccee787aac05f4ffaa342433b302d243aef6c820199a7be53b355	2025-08-10 20:23:49.747125+00	2025-08-03 20:23:49.41619+00	2025-08-03 20:23:49.41619+00	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36	127.0.0.1
fba93d35-cc79-422f-bffe-e9af99d309c5	ff40fb7e-b5b8-436a-b16f-cc4a31146ff5	22fdaef3148faf3849f54c0387ef828a134062db97ae3020c2256d5664336f40	2025-08-10 21:16:36.790447+00	2025-08-03 21:16:36.458719+00	2025-08-03 21:16:36.458719+00	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36	127.0.0.1
ac14edfe-6b11-4d24-90ab-23d863299600	ff40fb7e-b5b8-436a-b16f-cc4a31146ff5	08ee585e6ba5b826ec82dc103b2f0024332f92a6c23ed3f62adeb7727276c5c9	2025-08-10 21:26:55.20023+00	2025-08-03 21:26:54.90778+00	2025-08-03 21:26:54.90778+00	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36	127.0.0.1
e3cd4fae-b0e6-4aba-8c9c-4adce2c683b5	ff40fb7e-b5b8-436a-b16f-cc4a31146ff5	a2cf9bc8d5043452ae4c5e27163f8215cfdb916594f29e5f89fd0fced2fea45d	2025-08-10 21:30:06.837474+00	2025-08-03 21:30:06.551803+00	2025-08-03 21:30:06.551803+00	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36	127.0.0.1
be744205-154c-4bc3-a3f5-ebb8164c549c	ff40fb7e-b5b8-436a-b16f-cc4a31146ff5	3925e0eabc66075e22be696c65230e2d30c0eeeb7bda0ea882adb9329491c6a2	2025-08-10 21:56:55.047222+00	2025-08-03 21:56:54.713601+00	2025-08-03 21:56:54.713601+00	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36	127.0.0.1
2e59e3e2-9543-4a92-82e8-9ad9d45d4711	ff40fb7e-b5b8-436a-b16f-cc4a31146ff5	019bef90f9a40b15d4f2c01be86338361a0a4df97ba59e3dd5078888152e69db	2025-08-10 22:35:05.535114+00	2025-08-03 22:35:05.194974+00	2025-08-03 22:35:05.194974+00	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36	127.0.0.1
75ef171d-6d5b-4ccf-9a73-25f4263abb8f	ff40fb7e-b5b8-436a-b16f-cc4a31146ff5	38170ae03002bbfefa523167e4fc617949b128de8889af0b56df18071d42851a	2025-08-10 23:06:31.016281+00	2025-08-03 23:06:30.731873+00	2025-08-03 23:06:30.731873+00	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36	127.0.0.1
83452cbe-c2f4-4894-afd0-274a44e8f04d	ff40fb7e-b5b8-436a-b16f-cc4a31146ff5	5dc6944cf5f7e563ffde8bcd60fa0fee37f321344980fe15ecb5caac6be044fd	2025-08-10 23:38:29.079989+00	2025-08-03 23:38:28.762218+00	2025-08-03 23:38:28.762218+00	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36	127.0.0.1
6c7b6bd6-e885-4088-a7cf-06680f46a13a	ff40fb7e-b5b8-436a-b16f-cc4a31146ff5	f79432633bb087ed60886af1e080929da219f27628e1abb02b6ff077ff40f28e	2025-08-10 23:45:20.398904+00	2025-08-03 23:45:20.083641+00	2025-08-03 23:45:20.083641+00	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36	127.0.0.1
\.


--
-- Data for Name: user_sessions_detailed; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.user_sessions_detailed (id, user_id, session_token, start_time, end_time, duration_minutes, pages_visited, features_used, projects_accessed, papers_accessed, device_type, browser, ip_address, referrer, exit_page) FROM stdin;
\.


--
-- Data for Name: user_tags; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.user_tags (id, user_id, name, color, created_at) FROM stdin;
\.


--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.users (id, name, email, password, public_key, email_verified, accepted_terms, interests, intro, created_at, updated_at, last_login, deleted_at) FROM stdin;
ff40fb7e-b5b8-436a-b16f-cc4a31146ff5	Yashwardhan Chaudhuri	chaudhuri.yash@gmail.com	$2b$12$88HtovTpwqlUk1Z2PK8ZKOVLjIJ0CMkM6OnxcmEVWMpp3hH5n6TqW	\N	t	t	{}	Fill in your information	2025-08-03 19:32:00.907162+00	2025-08-03 23:45:20.083641+00	2025-08-03 23:45:20.406727+00	\N
\.


--
-- Name: ab_test_participants ab_test_participants_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ab_test_participants
    ADD CONSTRAINT ab_test_participants_pkey PRIMARY KEY (id);


--
-- Name: audit_log audit_log_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.audit_log
    ADD CONSTRAINT audit_log_pkey PRIMARY KEY (id);


--
-- Name: autosave_queue autosave_queue_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.autosave_queue
    ADD CONSTRAINT autosave_queue_pkey PRIMARY KEY (id);


--
-- Name: branch_permissions branch_permissions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.branch_permissions
    ADD CONSTRAINT branch_permissions_pkey PRIMARY KEY (id);


--
-- Name: branches branches_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.branches
    ADD CONSTRAINT branches_pkey PRIMARY KEY (id);


--
-- Name: conversations conversations_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.conversations
    ADD CONSTRAINT conversations_pkey PRIMARY KEY (id);


--
-- Name: diagnostics diagnostics_paper_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.diagnostics
    ADD CONSTRAINT diagnostics_paper_id_key UNIQUE (paper_id);


--
-- Name: diagnostics diagnostics_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.diagnostics
    ADD CONSTRAINT diagnostics_pkey PRIMARY KEY (id);


--
-- Name: document_sessions document_sessions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.document_sessions
    ADD CONSTRAINT document_sessions_pkey PRIMARY KEY (id);


--
-- Name: document_sessions document_sessions_session_token_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.document_sessions
    ADD CONSTRAINT document_sessions_session_token_key UNIQUE (session_token);


--
-- Name: email_verification_tokens email_verification_tokens_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.email_verification_tokens
    ADD CONSTRAINT email_verification_tokens_pkey PRIMARY KEY (id);


--
-- Name: email_verification_tokens email_verification_tokens_token_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.email_verification_tokens
    ADD CONSTRAINT email_verification_tokens_token_key UNIQUE (token);


--
-- Name: feature_analytics feature_analytics_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.feature_analytics
    ADD CONSTRAINT feature_analytics_pkey PRIMARY KEY (id);


--
-- Name: file_uploads file_uploads_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.file_uploads
    ADD CONSTRAINT file_uploads_pkey PRIMARY KEY (id);


--
-- Name: git_repositories git_repositories_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.git_repositories
    ADD CONSTRAINT git_repositories_pkey PRIMARY KEY (id);


--
-- Name: git_repositories git_repositories_project_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.git_repositories
    ADD CONSTRAINT git_repositories_project_id_key UNIQUE (project_id);


--
-- Name: graphs graphs_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.graphs
    ADD CONSTRAINT graphs_pkey PRIMARY KEY (id);


--
-- Name: highlights highlights_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.highlights
    ADD CONSTRAINT highlights_pkey PRIMARY KEY (id);


--
-- Name: invitation_reminders invitation_reminders_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.invitation_reminders
    ADD CONSTRAINT invitation_reminders_pkey PRIMARY KEY (id);


--
-- Name: latex_comments latex_comments_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.latex_comments
    ADD CONSTRAINT latex_comments_pkey PRIMARY KEY (id);


--
-- Name: latex_commits latex_commits_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.latex_commits
    ADD CONSTRAINT latex_commits_pkey PRIMARY KEY (id);


--
-- Name: latex_conflicts latex_conflicts_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.latex_conflicts
    ADD CONSTRAINT latex_conflicts_pkey PRIMARY KEY (id);


--
-- Name: latex_files latex_files_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.latex_files
    ADD CONSTRAINT latex_files_pkey PRIMARY KEY (id);


--
-- Name: latex_snapshots latex_snapshots_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.latex_snapshots
    ADD CONSTRAINT latex_snapshots_pkey PRIMARY KEY (id);


--
-- Name: notes notes_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.notes
    ADD CONSTRAINT notes_pkey PRIMARY KEY (id);


--
-- Name: paper_embeddings paper_embeddings_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.paper_embeddings
    ADD CONSTRAINT paper_embeddings_pkey PRIMARY KEY (id);


--
-- Name: papers papers_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.papers
    ADD CONSTRAINT papers_pkey PRIMARY KEY (id);


--
-- Name: password_reset_tokens password_reset_tokens_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.password_reset_tokens
    ADD CONSTRAINT password_reset_tokens_pkey PRIMARY KEY (id);


--
-- Name: password_reset_tokens password_reset_tokens_token_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.password_reset_tokens
    ADD CONSTRAINT password_reset_tokens_token_key UNIQUE (token);


--
-- Name: performance_metrics performance_metrics_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.performance_metrics
    ADD CONSTRAINT performance_metrics_pkey PRIMARY KEY (id);


--
-- Name: project_collaborators project_collaborators_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.project_collaborators
    ADD CONSTRAINT project_collaborators_pkey PRIMARY KEY (project_id, user_id);


--
-- Name: project_invitations project_invitations_invitation_token_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.project_invitations
    ADD CONSTRAINT project_invitations_invitation_token_key UNIQUE (invitation_token);


--
-- Name: project_invitations project_invitations_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.project_invitations
    ADD CONSTRAINT project_invitations_pkey PRIMARY KEY (id);


--
-- Name: project_members project_members_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.project_members
    ADD CONSTRAINT project_members_pkey PRIMARY KEY (id);


--
-- Name: project_papers project_papers_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.project_papers
    ADD CONSTRAINT project_papers_pkey PRIMARY KEY (project_id, paper_id);


--
-- Name: projects projects_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.projects
    ADD CONSTRAINT projects_pkey PRIMARY KEY (id);


--
-- Name: system_settings system_settings_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.system_settings
    ADD CONSTRAINT system_settings_pkey PRIMARY KEY (key);


--
-- Name: task_activity task_activity_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.task_activity
    ADD CONSTRAINT task_activity_pkey PRIMARY KEY (id);


--
-- Name: task_assignees task_assignees_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.task_assignees
    ADD CONSTRAINT task_assignees_pkey PRIMARY KEY (task_id, user_id);


--
-- Name: task_attachments task_attachments_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.task_attachments
    ADD CONSTRAINT task_attachments_pkey PRIMARY KEY (id);


--
-- Name: task_comments task_comments_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.task_comments
    ADD CONSTRAINT task_comments_pkey PRIMARY KEY (id);


--
-- Name: task_dependencies task_dependencies_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.task_dependencies
    ADD CONSTRAINT task_dependencies_pkey PRIMARY KEY (id);


--
-- Name: task_lists task_lists_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.task_lists
    ADD CONSTRAINT task_lists_pkey PRIMARY KEY (id);


--
-- Name: task_recurrence task_recurrence_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.task_recurrence
    ADD CONSTRAINT task_recurrence_pkey PRIMARY KEY (id);


--
-- Name: task_tags task_tags_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.task_tags
    ADD CONSTRAINT task_tags_pkey PRIMARY KEY (task_id, tag_id, user_id);


--
-- Name: task_time_logs task_time_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.task_time_logs
    ADD CONSTRAINT task_time_logs_pkey PRIMARY KEY (id);


--
-- Name: task_watchers task_watchers_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.task_watchers
    ADD CONSTRAINT task_watchers_pkey PRIMARY KEY (task_id, user_id);


--
-- Name: tasks tasks_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tasks
    ADD CONSTRAINT tasks_pkey PRIMARY KEY (id);


--
-- Name: latex_files unique_branch_file_path; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.latex_files
    ADD CONSTRAINT unique_branch_file_path UNIQUE (branch_id, file_path);


--
-- Name: branch_permissions unique_branch_user_permission; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.branch_permissions
    ADD CONSTRAINT unique_branch_user_permission UNIQUE (branch_id, user_id);


--
-- Name: task_dependencies unique_dependency; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.task_dependencies
    ADD CONSTRAINT unique_dependency UNIQUE (predecessor_task_id, successor_task_id);


--
-- Name: feature_analytics unique_feature_date; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.feature_analytics
    ADD CONSTRAINT unique_feature_date UNIQUE (feature_name, date);


--
-- Name: paper_embeddings unique_paper_embedding; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.paper_embeddings
    ADD CONSTRAINT unique_paper_embedding UNIQUE (paper_id);


--
-- Name: branches unique_project_branch_name; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.branches
    ADD CONSTRAINT unique_project_branch_name UNIQUE (project_id, name);


--
-- Name: graphs unique_project_graph; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.graphs
    ADD CONSTRAINT unique_project_graph UNIQUE (project_id);


--
-- Name: user_engagement_daily unique_user_date; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_engagement_daily
    ADD CONSTRAINT unique_user_date UNIQUE (user_id, date);


--
-- Name: project_members unique_user_project; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.project_members
    ADD CONSTRAINT unique_user_project UNIQUE (user_id, project_id);


--
-- Name: user_saved_searches unique_user_search_name; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_saved_searches
    ADD CONSTRAINT unique_user_search_name UNIQUE (user_id, name);


--
-- Name: user_tags unique_user_tag_name; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_tags
    ADD CONSTRAINT unique_user_tag_name UNIQUE (user_id, name);


--
-- Name: ab_test_participants unique_user_test; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ab_test_participants
    ADD CONSTRAINT unique_user_test UNIQUE (user_id, test_name);


--
-- Name: user_behavior_patterns user_behavior_patterns_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_behavior_patterns
    ADD CONSTRAINT user_behavior_patterns_pkey PRIMARY KEY (id);


--
-- Name: user_engagement_daily user_engagement_daily_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_engagement_daily
    ADD CONSTRAINT user_engagement_daily_pkey PRIMARY KEY (id);


--
-- Name: user_feature_usage user_feature_usage_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_feature_usage
    ADD CONSTRAINT user_feature_usage_pkey PRIMARY KEY (id);


--
-- Name: user_paper_tags user_paper_tags_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_paper_tags
    ADD CONSTRAINT user_paper_tags_pkey PRIMARY KEY (user_id, paper_id, tag_id);


--
-- Name: user_project_tags user_project_tags_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_project_tags
    ADD CONSTRAINT user_project_tags_pkey PRIMARY KEY (user_id, project_id, tag_id);


--
-- Name: user_saved_searches user_saved_searches_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_saved_searches
    ADD CONSTRAINT user_saved_searches_pkey PRIMARY KEY (id);


--
-- Name: user_sessions_detailed user_sessions_detailed_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_sessions_detailed
    ADD CONSTRAINT user_sessions_detailed_pkey PRIMARY KEY (id);


--
-- Name: user_sessions user_sessions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_sessions
    ADD CONSTRAINT user_sessions_pkey PRIMARY KEY (id);


--
-- Name: user_sessions user_sessions_token_hash_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_sessions
    ADD CONSTRAINT user_sessions_token_hash_key UNIQUE (token_hash);


--
-- Name: user_tags user_tags_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_tags
    ADD CONSTRAINT user_tags_pkey PRIMARY KEY (id);


--
-- Name: users users_email_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_email_key UNIQUE (email);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: idx_ab_test_participants_test_name; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_ab_test_participants_test_name ON public.ab_test_participants USING btree (test_name);


--
-- Name: idx_ab_test_participants_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_ab_test_participants_user_id ON public.ab_test_participants USING btree (user_id);


--
-- Name: idx_audit_log_created_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_audit_log_created_at ON public.audit_log USING btree (created_at);


--
-- Name: idx_audit_log_entity_type_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_audit_log_entity_type_id ON public.audit_log USING btree (entity_type, entity_id);


--
-- Name: idx_audit_log_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_audit_log_user_id ON public.audit_log USING btree (user_id);


--
-- Name: idx_autosave_queue_branch_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_autosave_queue_branch_id ON public.autosave_queue USING btree (branch_id);


--
-- Name: idx_autosave_queue_file_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_autosave_queue_file_id ON public.autosave_queue USING btree (file_id);


--
-- Name: idx_autosave_queue_priority; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_autosave_queue_priority ON public.autosave_queue USING btree (priority);


--
-- Name: idx_autosave_queue_scheduled_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_autosave_queue_scheduled_at ON public.autosave_queue USING btree (scheduled_at);


--
-- Name: idx_autosave_queue_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_autosave_queue_status ON public.autosave_queue USING btree (status);


--
-- Name: idx_branch_permissions_branch_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_branch_permissions_branch_id ON public.branch_permissions USING btree (branch_id);


--
-- Name: idx_branch_permissions_can_write; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_branch_permissions_can_write ON public.branch_permissions USING btree (can_write);


--
-- Name: idx_branch_permissions_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_branch_permissions_user_id ON public.branch_permissions USING btree (user_id);


--
-- Name: idx_branches_created_by; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_branches_created_by ON public.branches USING btree (created_by);


--
-- Name: idx_branches_name; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_branches_name ON public.branches USING btree (name);


--
-- Name: idx_branches_project_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_branches_project_id ON public.branches USING btree (project_id);


--
-- Name: idx_branches_source_branch_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_branches_source_branch_id ON public.branches USING btree (source_branch_id);


--
-- Name: idx_branches_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_branches_status ON public.branches USING btree (status);


--
-- Name: idx_conversations_created_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_conversations_created_at ON public.conversations USING btree (created_at);


--
-- Name: idx_conversations_created_by; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_conversations_created_by ON public.conversations USING btree (created_by);


--
-- Name: idx_conversations_type; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_conversations_type ON public.conversations USING btree (type);


--
-- Name: idx_diagnostics_paper_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_diagnostics_paper_id ON public.diagnostics USING btree (paper_id);


--
-- Name: idx_document_sessions_expires_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_document_sessions_expires_at ON public.document_sessions USING btree (expires_at);


--
-- Name: idx_document_sessions_file_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_document_sessions_file_id ON public.document_sessions USING btree (file_id);


--
-- Name: idx_document_sessions_last_activity; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_document_sessions_last_activity ON public.document_sessions USING btree (last_activity);


--
-- Name: idx_document_sessions_session_token; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_document_sessions_session_token ON public.document_sessions USING btree (session_token);


--
-- Name: idx_email_verification_tokens_active; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_email_verification_tokens_active ON public.email_verification_tokens USING btree (user_id);


--
-- Name: idx_email_verification_tokens_expires_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_email_verification_tokens_expires_at ON public.email_verification_tokens USING btree (expires_at);


--
-- Name: idx_email_verification_tokens_token; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_email_verification_tokens_token ON public.email_verification_tokens USING btree (token);


--
-- Name: idx_feature_analytics_date; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_feature_analytics_date ON public.feature_analytics USING btree (date);


--
-- Name: idx_feature_analytics_feature_name; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_feature_analytics_feature_name ON public.feature_analytics USING btree (feature_name);


--
-- Name: idx_git_repositories_default_branch_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_git_repositories_default_branch_id ON public.git_repositories USING btree (default_branch_id);


--
-- Name: idx_git_repositories_project_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_git_repositories_project_id ON public.git_repositories USING btree (project_id);


--
-- Name: idx_graphs_created_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_graphs_created_at ON public.graphs USING btree (created_at);


--
-- Name: idx_graphs_graph_type; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_graphs_graph_type ON public.graphs USING btree (graph_type);


--
-- Name: idx_graphs_project_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_graphs_project_id ON public.graphs USING btree (project_id);


--
-- Name: idx_highlights_created_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_highlights_created_at ON public.highlights USING btree (created_at);


--
-- Name: idx_highlights_paper_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_highlights_paper_id ON public.highlights USING btree (paper_id);


--
-- Name: idx_highlights_project_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_highlights_project_id ON public.highlights USING btree (project_id);


--
-- Name: idx_highlights_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_highlights_user_id ON public.highlights USING btree (user_id);


--
-- Name: idx_invitation_reminders_invitation_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_invitation_reminders_invitation_id ON public.invitation_reminders USING btree (invitation_id);


--
-- Name: idx_invitation_reminders_sent_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_invitation_reminders_sent_at ON public.invitation_reminders USING btree (sent_at);


--
-- Name: idx_latex_comments_commit_hash; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_latex_comments_commit_hash ON public.latex_comments USING btree (commit_hash);


--
-- Name: idx_latex_comments_project_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_latex_comments_project_id ON public.latex_comments USING btree (project_id);


--
-- Name: idx_latex_comments_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_latex_comments_user_id ON public.latex_comments USING btree (user_id);


--
-- Name: idx_latex_commits_created_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_latex_commits_created_at ON public.latex_commits USING btree (created_at);


--
-- Name: idx_latex_commits_project_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_latex_commits_project_id ON public.latex_commits USING btree (project_id);


--
-- Name: idx_latex_commits_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_latex_commits_user_id ON public.latex_commits USING btree (user_id);


--
-- Name: idx_latex_conflicts_project_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_latex_conflicts_project_id ON public.latex_conflicts USING btree (project_id);


--
-- Name: idx_latex_files_branch_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_latex_files_branch_id ON public.latex_files USING btree (branch_id);


--
-- Name: idx_latex_files_created_by; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_latex_files_created_by ON public.latex_files USING btree (created_by);


--
-- Name: idx_latex_files_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_latex_files_deleted_at ON public.latex_files USING btree (deleted_at);


--
-- Name: idx_latex_files_file_path; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_latex_files_file_path ON public.latex_files USING btree (file_path);


--
-- Name: idx_latex_files_file_type; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_latex_files_file_type ON public.latex_files USING btree (file_type);


--
-- Name: idx_latex_files_project_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_latex_files_project_id ON public.latex_files USING btree (project_id);


--
-- Name: idx_latex_snapshots_project_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_latex_snapshots_project_id ON public.latex_snapshots USING btree (project_id);


--
-- Name: idx_notes_created_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_notes_created_at ON public.notes USING btree (created_at);


--
-- Name: idx_notes_paper_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_notes_paper_id ON public.notes USING btree (paper_id);


--
-- Name: idx_notes_project_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_notes_project_id ON public.notes USING btree (project_id);


--
-- Name: idx_notes_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_notes_user_id ON public.notes USING btree (user_id);


--
-- Name: idx_paper_embeddings_abstract_cosine; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_paper_embeddings_abstract_cosine ON public.paper_embeddings USING hnsw (abstract_embedding public.vector_cosine_ops);


--
-- Name: idx_paper_embeddings_combined_cosine; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_paper_embeddings_combined_cosine ON public.paper_embeddings USING hnsw (combined_embedding public.vector_cosine_ops);


--
-- Name: idx_paper_embeddings_model; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_paper_embeddings_model ON public.paper_embeddings USING btree (embedding_model);


--
-- Name: idx_paper_embeddings_paper_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_paper_embeddings_paper_id ON public.paper_embeddings USING btree (paper_id);


--
-- Name: idx_paper_embeddings_title_cosine; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_paper_embeddings_title_cosine ON public.paper_embeddings USING hnsw (title_embedding public.vector_cosine_ops);


--
-- Name: idx_papers_authors; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_papers_authors ON public.papers USING gin (authors);


--
-- Name: idx_papers_created_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_papers_created_at ON public.papers USING btree (created_at);


--
-- Name: idx_papers_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_papers_deleted_at ON public.papers USING btree (deleted_at);


--
-- Name: idx_papers_keywords; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_papers_keywords ON public.papers USING gin (keywords);


--
-- Name: idx_papers_title; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_papers_title ON public.papers USING btree (title);


--
-- Name: idx_password_reset_tokens_expires_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_password_reset_tokens_expires_at ON public.password_reset_tokens USING btree (expires_at);


--
-- Name: idx_password_reset_tokens_token; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_password_reset_tokens_token ON public.password_reset_tokens USING btree (token);


--
-- Name: idx_performance_metrics_metric_name; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_performance_metrics_metric_name ON public.performance_metrics USING btree (metric_name);


--
-- Name: idx_performance_metrics_recorded_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_performance_metrics_recorded_at ON public.performance_metrics USING btree (recorded_at);


--
-- Name: idx_project_collaborators_project_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_project_collaborators_project_id ON public.project_collaborators USING btree (project_id);


--
-- Name: idx_project_collaborators_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_project_collaborators_user_id ON public.project_collaborators USING btree (user_id);


--
-- Name: idx_project_invitations_created_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_project_invitations_created_at ON public.project_invitations USING btree (created_at);


--
-- Name: idx_project_invitations_email; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_project_invitations_email ON public.project_invitations USING btree (email);


--
-- Name: idx_project_invitations_expires_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_project_invitations_expires_at ON public.project_invitations USING btree (expires_at);


--
-- Name: idx_project_invitations_invited_by; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_project_invitations_invited_by ON public.project_invitations USING btree (invited_by);


--
-- Name: idx_project_invitations_pending; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_project_invitations_pending ON public.project_invitations USING btree (project_id, email);


--
-- Name: idx_project_invitations_project_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_project_invitations_project_id ON public.project_invitations USING btree (project_id);


--
-- Name: idx_project_invitations_token; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_project_invitations_token ON public.project_invitations USING btree (invitation_token);


--
-- Name: idx_project_members_project_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_project_members_project_id ON public.project_members USING btree (project_id);


--
-- Name: idx_project_members_role; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_project_members_role ON public.project_members USING btree (role);


--
-- Name: idx_project_members_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_project_members_user_id ON public.project_members USING btree (user_id);


--
-- Name: idx_projects_created_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_projects_created_at ON public.projects USING btree (created_at);


--
-- Name: idx_projects_created_by; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_projects_created_by ON public.projects USING btree (created_by);


--
-- Name: idx_projects_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_projects_deleted_at ON public.projects USING btree (deleted_at);


--
-- Name: idx_projects_slug; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_projects_slug ON public.projects USING btree (slug);


--
-- Name: idx_task_activity_created_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_task_activity_created_at ON public.task_activity USING btree (created_at);


--
-- Name: idx_task_activity_task_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_task_activity_task_id ON public.task_activity USING btree (task_id);


--
-- Name: idx_task_activity_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_task_activity_user_id ON public.task_activity USING btree (user_id);


--
-- Name: idx_task_assignees_task_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_task_assignees_task_id ON public.task_assignees USING btree (task_id);


--
-- Name: idx_task_assignees_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_task_assignees_user_id ON public.task_assignees USING btree (user_id);


--
-- Name: idx_task_attachments_file_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_task_attachments_file_id ON public.task_attachments USING btree (file_id);


--
-- Name: idx_task_attachments_paper_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_task_attachments_paper_id ON public.task_attachments USING btree (paper_id);


--
-- Name: idx_task_attachments_task_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_task_attachments_task_id ON public.task_attachments USING btree (task_id);


--
-- Name: idx_task_comments_created_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_task_comments_created_at ON public.task_comments USING btree (created_at);


--
-- Name: idx_task_comments_reply_to; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_task_comments_reply_to ON public.task_comments USING btree (reply_to);


--
-- Name: idx_task_comments_task_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_task_comments_task_id ON public.task_comments USING btree (task_id);


--
-- Name: idx_task_comments_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_task_comments_user_id ON public.task_comments USING btree (user_id);


--
-- Name: idx_task_dependencies_predecessor; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_task_dependencies_predecessor ON public.task_dependencies USING btree (predecessor_task_id);


--
-- Name: idx_task_dependencies_successor; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_task_dependencies_successor ON public.task_dependencies USING btree (successor_task_id);


--
-- Name: idx_task_lists_position; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_task_lists_position ON public.task_lists USING btree ("position");


--
-- Name: idx_task_lists_project_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_task_lists_project_id ON public.task_lists USING btree (project_id);


--
-- Name: idx_task_recurrence_task_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_task_recurrence_task_id ON public.task_recurrence USING btree (task_id);


--
-- Name: idx_task_tags_tag_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_task_tags_tag_id ON public.task_tags USING btree (tag_id);


--
-- Name: idx_task_tags_task_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_task_tags_task_id ON public.task_tags USING btree (task_id);


--
-- Name: idx_task_tags_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_task_tags_user_id ON public.task_tags USING btree (user_id);


--
-- Name: idx_task_time_logs_log_date; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_task_time_logs_log_date ON public.task_time_logs USING btree (log_date);


--
-- Name: idx_task_time_logs_task_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_task_time_logs_task_id ON public.task_time_logs USING btree (task_id);


--
-- Name: idx_task_time_logs_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_task_time_logs_user_id ON public.task_time_logs USING btree (user_id);


--
-- Name: idx_task_watchers_task_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_task_watchers_task_id ON public.task_watchers USING btree (task_id);


--
-- Name: idx_task_watchers_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_task_watchers_user_id ON public.task_watchers USING btree (user_id);


--
-- Name: idx_tasks_assigned_to; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_tasks_assigned_to ON public.tasks USING btree (assigned_to);


--
-- Name: idx_tasks_created_by; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_tasks_created_by ON public.tasks USING btree (created_by);


--
-- Name: idx_tasks_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_tasks_deleted_at ON public.tasks USING btree (deleted_at);


--
-- Name: idx_tasks_due_date; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_tasks_due_date ON public.tasks USING btree (due_date);


--
-- Name: idx_tasks_parent_task_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_tasks_parent_task_id ON public.tasks USING btree (parent_task_id);


--
-- Name: idx_tasks_position; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_tasks_position ON public.tasks USING btree ("position");


--
-- Name: idx_tasks_priority; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_tasks_priority ON public.tasks USING btree (priority);


--
-- Name: idx_tasks_project_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_tasks_project_id ON public.tasks USING btree (project_id);


--
-- Name: idx_tasks_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_tasks_status ON public.tasks USING btree (status);


--
-- Name: idx_tasks_task_list_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_tasks_task_list_id ON public.tasks USING btree (task_list_id);


--
-- Name: idx_user_behavior_patterns_pattern_type; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_user_behavior_patterns_pattern_type ON public.user_behavior_patterns USING btree (pattern_type);


--
-- Name: idx_user_behavior_patterns_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_user_behavior_patterns_user_id ON public.user_behavior_patterns USING btree (user_id);


--
-- Name: idx_user_engagement_daily_date; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_user_engagement_daily_date ON public.user_engagement_daily USING btree (date);


--
-- Name: idx_user_engagement_daily_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_user_engagement_daily_user_id ON public.user_engagement_daily USING btree (user_id);


--
-- Name: idx_user_feature_usage_created_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_user_feature_usage_created_at ON public.user_feature_usage USING btree (created_at);


--
-- Name: idx_user_feature_usage_feature_name; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_user_feature_usage_feature_name ON public.user_feature_usage USING btree (feature_name);


--
-- Name: idx_user_feature_usage_session_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_user_feature_usage_session_id ON public.user_feature_usage USING btree (session_id);


--
-- Name: idx_user_feature_usage_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_user_feature_usage_user_id ON public.user_feature_usage USING btree (user_id);


--
-- Name: idx_user_paper_tags_paper_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_user_paper_tags_paper_id ON public.user_paper_tags USING btree (paper_id);


--
-- Name: idx_user_paper_tags_tag_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_user_paper_tags_tag_id ON public.user_paper_tags USING btree (tag_id);


--
-- Name: idx_user_paper_tags_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_user_paper_tags_user_id ON public.user_paper_tags USING btree (user_id);


--
-- Name: idx_user_project_tags_project_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_user_project_tags_project_id ON public.user_project_tags USING btree (project_id);


--
-- Name: idx_user_project_tags_tag_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_user_project_tags_tag_id ON public.user_project_tags USING btree (tag_id);


--
-- Name: idx_user_project_tags_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_user_project_tags_user_id ON public.user_project_tags USING btree (user_id);


--
-- Name: idx_user_saved_searches_created_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_user_saved_searches_created_at ON public.user_saved_searches USING btree (created_at);


--
-- Name: idx_user_saved_searches_name; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_user_saved_searches_name ON public.user_saved_searches USING btree (name);


--
-- Name: idx_user_saved_searches_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_user_saved_searches_user_id ON public.user_saved_searches USING btree (user_id);


--
-- Name: idx_user_sessions_detailed_session_token; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_user_sessions_detailed_session_token ON public.user_sessions_detailed USING btree (session_token);


--
-- Name: idx_user_sessions_detailed_start_time; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_user_sessions_detailed_start_time ON public.user_sessions_detailed USING btree (start_time);


--
-- Name: idx_user_sessions_detailed_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_user_sessions_detailed_user_id ON public.user_sessions_detailed USING btree (user_id);


--
-- Name: idx_user_sessions_expires_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_user_sessions_expires_at ON public.user_sessions USING btree (expires_at);


--
-- Name: idx_user_sessions_token_hash; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_user_sessions_token_hash ON public.user_sessions USING btree (token_hash);


--
-- Name: idx_user_sessions_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_user_sessions_user_id ON public.user_sessions USING btree (user_id);


--
-- Name: idx_user_tags_name; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_user_tags_name ON public.user_tags USING btree (name);


--
-- Name: idx_user_tags_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_user_tags_user_id ON public.user_tags USING btree (user_id);


--
-- Name: idx_users_created_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_users_created_at ON public.users USING btree (created_at);


--
-- Name: idx_users_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_users_deleted_at ON public.users USING btree (deleted_at);


--
-- Name: idx_users_email; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_users_email ON public.users USING btree (email);


--
-- Name: ix_projects_created_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_projects_created_at ON public.projects USING btree (created_at);


--
-- Name: ix_projects_created_by; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_projects_created_by ON public.projects USING btree (created_by);


--
-- Name: ix_projects_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_projects_deleted_at ON public.projects USING btree (deleted_at);


--
-- Name: ix_projects_slug_unique_active; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_projects_slug_unique_active ON public.projects USING btree (slug) WHERE (deleted_at IS NULL);


--
-- Name: branches update_branches_updated_at; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER update_branches_updated_at BEFORE UPDATE ON public.branches FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: conversations update_conversations_updated_at; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER update_conversations_updated_at BEFORE UPDATE ON public.conversations FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: diagnostics update_diagnostics_updated_at; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER update_diagnostics_updated_at BEFORE UPDATE ON public.diagnostics FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: git_repositories update_git_repositories_updated_at; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER update_git_repositories_updated_at BEFORE UPDATE ON public.git_repositories FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: graphs update_graphs_updated_at; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER update_graphs_updated_at BEFORE UPDATE ON public.graphs FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: highlights update_highlights_updated_at; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER update_highlights_updated_at BEFORE UPDATE ON public.highlights FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: latex_comments update_latex_comments_updated_at; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER update_latex_comments_updated_at BEFORE UPDATE ON public.latex_comments FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: latex_files update_latex_files_updated_at; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER update_latex_files_updated_at BEFORE UPDATE ON public.latex_files FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: notes update_notes_updated_at; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER update_notes_updated_at BEFORE UPDATE ON public.notes FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: paper_embeddings update_paper_embeddings_updated_at; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER update_paper_embeddings_updated_at BEFORE UPDATE ON public.paper_embeddings FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: papers update_papers_updated_at; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER update_papers_updated_at BEFORE UPDATE ON public.papers FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: projects update_projects_updated_at; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER update_projects_updated_at BEFORE UPDATE ON public.projects FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: task_comments update_task_comments_updated_at; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER update_task_comments_updated_at BEFORE UPDATE ON public.task_comments FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: task_lists update_task_lists_updated_at; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER update_task_lists_updated_at BEFORE UPDATE ON public.task_lists FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: task_time_logs update_task_time_logs_updated_at; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER update_task_time_logs_updated_at BEFORE UPDATE ON public.task_time_logs FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: tasks update_tasks_updated_at; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER update_tasks_updated_at BEFORE UPDATE ON public.tasks FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: user_saved_searches update_user_saved_searches_updated_at; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER update_user_saved_searches_updated_at BEFORE UPDATE ON public.user_saved_searches FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: users update_users_updated_at; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON public.users FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: ab_test_participants ab_test_participants_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ab_test_participants
    ADD CONSTRAINT ab_test_participants_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: audit_log audit_log_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.audit_log
    ADD CONSTRAINT audit_log_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: autosave_queue autosave_queue_branch_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.autosave_queue
    ADD CONSTRAINT autosave_queue_branch_id_fkey FOREIGN KEY (branch_id) REFERENCES public.branches(id) ON DELETE CASCADE;


--
-- Name: autosave_queue autosave_queue_file_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.autosave_queue
    ADD CONSTRAINT autosave_queue_file_id_fkey FOREIGN KEY (file_id) REFERENCES public.latex_files(id) ON DELETE CASCADE;


--
-- Name: autosave_queue autosave_queue_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.autosave_queue
    ADD CONSTRAINT autosave_queue_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: branch_permissions branch_permissions_branch_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.branch_permissions
    ADD CONSTRAINT branch_permissions_branch_id_fkey FOREIGN KEY (branch_id) REFERENCES public.branches(id) ON DELETE CASCADE;


--
-- Name: branch_permissions branch_permissions_granted_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.branch_permissions
    ADD CONSTRAINT branch_permissions_granted_by_fkey FOREIGN KEY (granted_by) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: branch_permissions branch_permissions_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.branch_permissions
    ADD CONSTRAINT branch_permissions_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: branches branches_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.branches
    ADD CONSTRAINT branches_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: branches branches_merged_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.branches
    ADD CONSTRAINT branches_merged_by_fkey FOREIGN KEY (merged_by) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: branches branches_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.branches
    ADD CONSTRAINT branches_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id) ON DELETE CASCADE;


--
-- Name: branches branches_source_branch_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.branches
    ADD CONSTRAINT branches_source_branch_id_fkey FOREIGN KEY (source_branch_id) REFERENCES public.branches(id) ON DELETE SET NULL;


--
-- Name: conversations conversations_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.conversations
    ADD CONSTRAINT conversations_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: diagnostics diagnostics_paper_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.diagnostics
    ADD CONSTRAINT diagnostics_paper_id_fkey FOREIGN KEY (paper_id) REFERENCES public.papers(id) ON DELETE CASCADE;


--
-- Name: document_sessions document_sessions_file_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.document_sessions
    ADD CONSTRAINT document_sessions_file_id_fkey FOREIGN KEY (file_id) REFERENCES public.latex_files(id) ON DELETE CASCADE;


--
-- Name: email_verification_tokens email_verification_tokens_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.email_verification_tokens
    ADD CONSTRAINT email_verification_tokens_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: file_uploads file_uploads_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.file_uploads
    ADD CONSTRAINT file_uploads_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: user_paper_tags fk_user_paper_tags_user_tag; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_paper_tags
    ADD CONSTRAINT fk_user_paper_tags_user_tag FOREIGN KEY (tag_id) REFERENCES public.user_tags(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: user_project_tags fk_user_project_tags_user_tag; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_project_tags
    ADD CONSTRAINT fk_user_project_tags_user_tag FOREIGN KEY (tag_id) REFERENCES public.user_tags(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: git_repositories git_repositories_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.git_repositories
    ADD CONSTRAINT git_repositories_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id) ON DELETE CASCADE;


--
-- Name: graphs graphs_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.graphs
    ADD CONSTRAINT graphs_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id) ON DELETE CASCADE;


--
-- Name: highlights highlights_paper_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.highlights
    ADD CONSTRAINT highlights_paper_id_fkey FOREIGN KEY (paper_id) REFERENCES public.papers(id) ON DELETE CASCADE;


--
-- Name: highlights highlights_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.highlights
    ADD CONSTRAINT highlights_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id) ON DELETE CASCADE;


--
-- Name: highlights highlights_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.highlights
    ADD CONSTRAINT highlights_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: invitation_reminders invitation_reminders_invitation_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.invitation_reminders
    ADD CONSTRAINT invitation_reminders_invitation_id_fkey FOREIGN KEY (invitation_id) REFERENCES public.project_invitations(id) ON DELETE CASCADE;


--
-- Name: latex_comments latex_comments_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.latex_comments
    ADD CONSTRAINT latex_comments_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id) ON DELETE CASCADE;


--
-- Name: latex_comments latex_comments_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.latex_comments
    ADD CONSTRAINT latex_comments_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: latex_commits latex_commits_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.latex_commits
    ADD CONSTRAINT latex_commits_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id) ON DELETE CASCADE;


--
-- Name: latex_commits latex_commits_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.latex_commits
    ADD CONSTRAINT latex_commits_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: latex_conflicts latex_conflicts_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.latex_conflicts
    ADD CONSTRAINT latex_conflicts_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id) ON DELETE CASCADE;


--
-- Name: latex_conflicts latex_conflicts_resolved_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.latex_conflicts
    ADD CONSTRAINT latex_conflicts_resolved_by_fkey FOREIGN KEY (resolved_by) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: latex_files latex_files_branch_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.latex_files
    ADD CONSTRAINT latex_files_branch_id_fkey FOREIGN KEY (branch_id) REFERENCES public.branches(id) ON DELETE CASCADE;


--
-- Name: latex_files latex_files_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.latex_files
    ADD CONSTRAINT latex_files_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: latex_files latex_files_last_modified_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.latex_files
    ADD CONSTRAINT latex_files_last_modified_by_fkey FOREIGN KEY (last_modified_by) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: latex_files latex_files_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.latex_files
    ADD CONSTRAINT latex_files_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id) ON DELETE CASCADE;


--
-- Name: latex_snapshots latex_snapshots_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.latex_snapshots
    ADD CONSTRAINT latex_snapshots_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id) ON DELETE CASCADE;


--
-- Name: latex_snapshots latex_snapshots_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.latex_snapshots
    ADD CONSTRAINT latex_snapshots_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: notes notes_paper_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.notes
    ADD CONSTRAINT notes_paper_id_fkey FOREIGN KEY (paper_id) REFERENCES public.papers(id) ON DELETE CASCADE;


--
-- Name: notes notes_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.notes
    ADD CONSTRAINT notes_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id) ON DELETE CASCADE;


--
-- Name: notes notes_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.notes
    ADD CONSTRAINT notes_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: paper_embeddings paper_embeddings_paper_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.paper_embeddings
    ADD CONSTRAINT paper_embeddings_paper_id_fkey FOREIGN KEY (paper_id) REFERENCES public.papers(id) ON DELETE CASCADE;


--
-- Name: password_reset_tokens password_reset_tokens_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.password_reset_tokens
    ADD CONSTRAINT password_reset_tokens_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: project_collaborators project_collaborators_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.project_collaborators
    ADD CONSTRAINT project_collaborators_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id) ON DELETE CASCADE;


--
-- Name: project_collaborators project_collaborators_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.project_collaborators
    ADD CONSTRAINT project_collaborators_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: project_invitations project_invitations_accepted_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.project_invitations
    ADD CONSTRAINT project_invitations_accepted_by_fkey FOREIGN KEY (accepted_by) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: project_invitations project_invitations_cancelled_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.project_invitations
    ADD CONSTRAINT project_invitations_cancelled_by_fkey FOREIGN KEY (cancelled_by) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: project_invitations project_invitations_invited_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.project_invitations
    ADD CONSTRAINT project_invitations_invited_by_fkey FOREIGN KEY (invited_by) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: project_invitations project_invitations_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.project_invitations
    ADD CONSTRAINT project_invitations_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id) ON DELETE CASCADE;


--
-- Name: project_members project_members_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.project_members
    ADD CONSTRAINT project_members_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id) ON DELETE CASCADE;


--
-- Name: project_members project_members_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.project_members
    ADD CONSTRAINT project_members_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: project_papers project_papers_paper_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.project_papers
    ADD CONSTRAINT project_papers_paper_id_fkey FOREIGN KEY (paper_id) REFERENCES public.papers(id) ON DELETE CASCADE;


--
-- Name: project_papers project_papers_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.project_papers
    ADD CONSTRAINT project_papers_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id) ON DELETE CASCADE;


--
-- Name: projects projects_conversation_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.projects
    ADD CONSTRAINT projects_conversation_id_fkey FOREIGN KEY (conversation_id) REFERENCES public.conversations(id) ON DELETE SET NULL;


--
-- Name: projects projects_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.projects
    ADD CONSTRAINT projects_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: system_settings system_settings_updated_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.system_settings
    ADD CONSTRAINT system_settings_updated_by_fkey FOREIGN KEY (updated_by) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: task_activity task_activity_task_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.task_activity
    ADD CONSTRAINT task_activity_task_id_fkey FOREIGN KEY (task_id) REFERENCES public.tasks(id) ON DELETE CASCADE;


--
-- Name: task_activity task_activity_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.task_activity
    ADD CONSTRAINT task_activity_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: task_assignees task_assignees_assigned_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.task_assignees
    ADD CONSTRAINT task_assignees_assigned_by_fkey FOREIGN KEY (assigned_by) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: task_assignees task_assignees_task_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.task_assignees
    ADD CONSTRAINT task_assignees_task_id_fkey FOREIGN KEY (task_id) REFERENCES public.tasks(id) ON DELETE CASCADE;


--
-- Name: task_assignees task_assignees_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.task_assignees
    ADD CONSTRAINT task_assignees_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: task_attachments task_attachments_attached_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.task_attachments
    ADD CONSTRAINT task_attachments_attached_by_fkey FOREIGN KEY (attached_by) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: task_attachments task_attachments_file_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.task_attachments
    ADD CONSTRAINT task_attachments_file_id_fkey FOREIGN KEY (file_id) REFERENCES public.file_uploads(id) ON DELETE CASCADE;


--
-- Name: task_attachments task_attachments_paper_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.task_attachments
    ADD CONSTRAINT task_attachments_paper_id_fkey FOREIGN KEY (paper_id) REFERENCES public.papers(id) ON DELETE CASCADE;


--
-- Name: task_attachments task_attachments_task_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.task_attachments
    ADD CONSTRAINT task_attachments_task_id_fkey FOREIGN KEY (task_id) REFERENCES public.tasks(id) ON DELETE CASCADE;


--
-- Name: task_comments task_comments_reply_to_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.task_comments
    ADD CONSTRAINT task_comments_reply_to_fkey FOREIGN KEY (reply_to) REFERENCES public.task_comments(id) ON DELETE CASCADE;


--
-- Name: task_comments task_comments_task_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.task_comments
    ADD CONSTRAINT task_comments_task_id_fkey FOREIGN KEY (task_id) REFERENCES public.tasks(id) ON DELETE CASCADE;


--
-- Name: task_comments task_comments_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.task_comments
    ADD CONSTRAINT task_comments_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: task_dependencies task_dependencies_predecessor_task_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.task_dependencies
    ADD CONSTRAINT task_dependencies_predecessor_task_id_fkey FOREIGN KEY (predecessor_task_id) REFERENCES public.tasks(id) ON DELETE CASCADE;


--
-- Name: task_dependencies task_dependencies_successor_task_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.task_dependencies
    ADD CONSTRAINT task_dependencies_successor_task_id_fkey FOREIGN KEY (successor_task_id) REFERENCES public.tasks(id) ON DELETE CASCADE;


--
-- Name: task_lists task_lists_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.task_lists
    ADD CONSTRAINT task_lists_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: task_lists task_lists_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.task_lists
    ADD CONSTRAINT task_lists_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id) ON DELETE CASCADE;


--
-- Name: task_recurrence task_recurrence_task_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.task_recurrence
    ADD CONSTRAINT task_recurrence_task_id_fkey FOREIGN KEY (task_id) REFERENCES public.tasks(id) ON DELETE CASCADE;


--
-- Name: task_tags task_tags_tag_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.task_tags
    ADD CONSTRAINT task_tags_tag_id_fkey FOREIGN KEY (tag_id) REFERENCES public.user_tags(id) ON DELETE CASCADE;


--
-- Name: task_tags task_tags_task_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.task_tags
    ADD CONSTRAINT task_tags_task_id_fkey FOREIGN KEY (task_id) REFERENCES public.tasks(id) ON DELETE CASCADE;


--
-- Name: task_tags task_tags_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.task_tags
    ADD CONSTRAINT task_tags_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: task_time_logs task_time_logs_task_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.task_time_logs
    ADD CONSTRAINT task_time_logs_task_id_fkey FOREIGN KEY (task_id) REFERENCES public.tasks(id) ON DELETE CASCADE;


--
-- Name: task_time_logs task_time_logs_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.task_time_logs
    ADD CONSTRAINT task_time_logs_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: task_watchers task_watchers_task_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.task_watchers
    ADD CONSTRAINT task_watchers_task_id_fkey FOREIGN KEY (task_id) REFERENCES public.tasks(id) ON DELETE CASCADE;


--
-- Name: task_watchers task_watchers_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.task_watchers
    ADD CONSTRAINT task_watchers_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: tasks tasks_assigned_to_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tasks
    ADD CONSTRAINT tasks_assigned_to_fkey FOREIGN KEY (assigned_to) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: tasks tasks_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tasks
    ADD CONSTRAINT tasks_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: tasks tasks_parent_task_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tasks
    ADD CONSTRAINT tasks_parent_task_id_fkey FOREIGN KEY (parent_task_id) REFERENCES public.tasks(id) ON DELETE CASCADE;


--
-- Name: tasks tasks_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tasks
    ADD CONSTRAINT tasks_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id) ON DELETE CASCADE;


--
-- Name: tasks tasks_task_list_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tasks
    ADD CONSTRAINT tasks_task_list_id_fkey FOREIGN KEY (task_list_id) REFERENCES public.task_lists(id) ON DELETE SET NULL;


--
-- Name: user_behavior_patterns user_behavior_patterns_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_behavior_patterns
    ADD CONSTRAINT user_behavior_patterns_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: user_engagement_daily user_engagement_daily_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_engagement_daily
    ADD CONSTRAINT user_engagement_daily_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: user_feature_usage user_feature_usage_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_feature_usage
    ADD CONSTRAINT user_feature_usage_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: user_paper_tags user_paper_tags_paper_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_paper_tags
    ADD CONSTRAINT user_paper_tags_paper_id_fkey FOREIGN KEY (paper_id) REFERENCES public.papers(id) ON DELETE CASCADE;


--
-- Name: user_paper_tags user_paper_tags_tag_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_paper_tags
    ADD CONSTRAINT user_paper_tags_tag_id_fkey FOREIGN KEY (tag_id) REFERENCES public.user_tags(id) ON DELETE CASCADE;


--
-- Name: user_paper_tags user_paper_tags_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_paper_tags
    ADD CONSTRAINT user_paper_tags_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: user_project_tags user_project_tags_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_project_tags
    ADD CONSTRAINT user_project_tags_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id) ON DELETE CASCADE;


--
-- Name: user_project_tags user_project_tags_tag_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_project_tags
    ADD CONSTRAINT user_project_tags_tag_id_fkey FOREIGN KEY (tag_id) REFERENCES public.user_tags(id) ON DELETE CASCADE;


--
-- Name: user_project_tags user_project_tags_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_project_tags
    ADD CONSTRAINT user_project_tags_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: user_saved_searches user_saved_searches_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_saved_searches
    ADD CONSTRAINT user_saved_searches_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: user_sessions_detailed user_sessions_detailed_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_sessions_detailed
    ADD CONSTRAINT user_sessions_detailed_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: user_sessions user_sessions_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_sessions
    ADD CONSTRAINT user_sessions_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: user_tags user_tags_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_tags
    ADD CONSTRAINT user_tags_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

