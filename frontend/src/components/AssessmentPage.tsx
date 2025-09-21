import { Navigate, useParams } from "react-router-dom";

export default function AssessmentPage() {
  const params = useParams<{ dimensionId: string; themeId: string }>();
  const { dimensionId, themeId } = params;

  if (!dimensionId || !themeId) {
    return <Navigate to="/" replace />;
  }

  return <Navigate to={`/dimensions/${dimensionId}/themes/${themeId}/topics`} replace />;
}
