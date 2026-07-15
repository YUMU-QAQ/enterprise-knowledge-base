import { Routes, Route, Navigate } from "react-router-dom";
import { useAuthStore } from "./stores/authStore";
import AppLayout from "./components/AppLayout";
import LoginPage from "./features/auth/LoginPage";
import KnowledgePage from "./features/knowledge/KnowledgePage";
import SearchPage from "./features/search/SearchPage";
import DocumentPage from "./features/documents/DocumentPage";
import RecommendPage from "./features/recommend/RecommendPage";
import AdminPage from "./features/admin/AdminPage";
import AIChatPanel from "./components/AIChatPanel";

export default function App() {
  const token = useAuthStore((s) => s.token);

  if (!token) {
    return (
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    );
  }

  return (
    <AppLayout>
      <Routes>
        <Route path="/" element={<Navigate to="/knowledge" replace />} />
        <Route path="/knowledge" element={<KnowledgePage />} />
        <Route path="/search" element={<SearchPage />} />
        <Route path="/documents/:id" element={<DocumentPage />} />
        <Route path="/recommend" element={<RecommendPage />} />
        <Route path="/admin/*" element={<AdminPage />} />
      </Routes>
      <AIChatPanel />
    </AppLayout>
  );
}
