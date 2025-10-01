-- Database setup script for Vietnam Airlines Image Database Editor
-- Run these SQL commands in your Supabase SQL Editor

-- 1. Create users table for authentication and user management
CREATE TABLE IF NOT EXISTS users (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role VARCHAR(20) DEFAULT 'reviewer',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 2. Add new columns to existing images table for user assignment
ALTER TABLE images
ADD COLUMN IF NOT EXISTS assigned_to UUID REFERENCES users(id),
ADD COLUMN IF NOT EXISTS assigned_at TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS notes TEXT,
ADD COLUMN IF NOT EXISTS ref_image_url TEXT,
ADD COLUMN IF NOT EXISTS completed_at TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS reviewed_by UUID REFERENCES users(id);

-- 3. Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_images_assigned_to ON images(assigned_to);
CREATE INDEX IF NOT EXISTS idx_images_source_url ON images(source_url);
CREATE INDEX IF NOT EXISTS idx_images_status ON images(image_status);
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_active ON users(is_active);

-- 4. Create a trigger to update the updated_at column
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 5. Create a trigger to set completed_at when prompt is filled
CREATE OR REPLACE FUNCTION update_completed_at()
RETURNS TRIGGER AS $$
BEGIN
    -- If prompt was empty and is now filled, set completed_at
    IF (OLD.prompt IS NULL OR OLD.prompt = '') AND (NEW.prompt IS NOT NULL AND NEW.prompt != '') THEN
        NEW.completed_at = NOW();
    END IF;
    -- If prompt was filled and is now empty, clear completed_at
    IF (OLD.prompt IS NOT NULL AND OLD.prompt != '') AND (NEW.prompt IS NULL OR NEW.prompt = '') THEN
        NEW.completed_at = NULL;
    END IF;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_images_completed_at
    BEFORE UPDATE ON images
    FOR EACH ROW EXECUTE FUNCTION update_completed_at();

-- 6. Create admin user (change password after first login)
-- Note: This will create the first admin user. The password will be hashed by the application.
-- You'll need to run the application and use the create user function for this.

-- 7. Row Level Security (RLS) policies for multi-user access
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE images ENABLE ROW LEVEL SECURITY;

-- Users can see all users (for admin assignment purposes)
CREATE POLICY "Users can view all users" ON users FOR SELECT USING (true);

-- Only admins can create/update/delete users
CREATE POLICY "Only admins can modify users" ON users
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM users u
            WHERE u.id = auth.uid() AND u.role = 'admin' AND u.is_active = true
        )
    );

-- Users can see all images (for progress dashboard)
CREATE POLICY "Users can view all images" ON images FOR SELECT USING (true);

-- Users can only modify their assigned images
CREATE POLICY "Users can modify assigned images" ON images
    FOR UPDATE USING (
        assigned_to = auth.uid() OR
        EXISTS (
            SELECT 1 FROM users u
            WHERE u.id = auth.uid() AND u.role = 'admin' AND u.is_active = true
        )
    );

-- Admins can assign images
CREATE POLICY "Admins can assign images" ON images
    FOR UPDATE USING (
        EXISTS (
            SELECT 1 FROM users u
            WHERE u.id = auth.uid() AND u.role = 'admin' AND u.is_active = true
        )
    );

-- 8. Create useful views for reporting

-- Overall progress view
CREATE OR REPLACE VIEW progress_overview AS
SELECT
    (SELECT COUNT(*) FROM images) as total_images,
    (SELECT COUNT(*) FROM images WHERE assigned_to IS NOT NULL) as assigned_images,
    (SELECT COUNT(*) FROM images WHERE assigned_to IS NULL) as unassigned_images,
    (SELECT COUNT(*) FROM images WHERE prompt IS NOT NULL AND prompt != '') as completed_images,
    (SELECT COUNT(*) FROM images WHERE prompt IS NULL OR prompt = '') as pending_images,
    (SELECT ROUND(
        (COUNT(*) FILTER (WHERE prompt IS NOT NULL AND prompt != '') * 100.0) / COUNT(*), 2
    ) FROM images) as completion_percentage;

-- User progress view
CREATE OR REPLACE VIEW user_progress AS
SELECT
    u.id,
    u.username,
    u.role,
    COUNT(i.id) as assigned_count,
    COUNT(i.id) FILTER (WHERE i.prompt IS NOT NULL AND i.prompt != '') as completed_count,
    COUNT(i.id) FILTER (WHERE i.prompt IS NULL OR i.prompt = '') as pending_count,
    CASE
        WHEN COUNT(i.id) > 0 THEN
            ROUND((COUNT(i.id) FILTER (WHERE i.prompt IS NOT NULL AND i.prompt != '') * 100.0) / COUNT(i.id), 2)
        ELSE 0
    END as completion_percentage,
    MIN(i.assigned_at) as first_assigned,
    MAX(i.completed_at) as last_completed
FROM users u
LEFT JOIN images i ON u.id = i.assigned_to
WHERE u.is_active = true
GROUP BY u.id, u.username, u.role;

-- Source progress view
CREATE OR REPLACE VIEW source_progress AS
SELECT
    source_url,
    COUNT(*) as total_images,
    COUNT(*) FILTER (WHERE assigned_to IS NOT NULL) as assigned_images,
    COUNT(*) FILTER (WHERE prompt IS NOT NULL AND prompt != '') as completed_images,
    ROUND(
        (COUNT(*) FILTER (WHERE prompt IS NOT NULL AND prompt != '') * 100.0) / COUNT(*), 2
    ) as completion_percentage
FROM images
GROUP BY source_url
ORDER BY completion_percentage DESC;

COMMENT ON TABLE users IS 'User accounts for image review system';
COMMENT ON TABLE images IS 'Image metadata with assignment tracking';
COMMENT ON VIEW progress_overview IS 'Overall project progress statistics';
COMMENT ON VIEW user_progress IS 'Individual user progress statistics';
COMMENT ON VIEW source_progress IS 'Progress statistics by source URL';